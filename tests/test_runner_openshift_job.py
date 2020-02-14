# (c) 2012-2020, Ansible by Red Hat
#
# This file is part of Ansible Galaxy
#
# Ansible Galaxy is free software: you can redistribute it and/or modify
# it under the terms of the Apache License as published by
# the Apache Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Ansible Galaxy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Apache License for more details.
#
# You should have received a copy of the Apache License
# along with Galaxy.  If not, see <http://www.apache.org/licenses/>.

from types import SimpleNamespace

import pytest
from pytest_mock import mocker  # noqa F401
import requests

from galaxy_importer import exceptions as exc
from galaxy_importer.ansible_test.runners import openshift_job


@pytest.fixture
def job():
    return openshift_job.Job(
        'my_domain', 'my_ns', 'session_token', 'image', 'job_template', logger=None)


def test_runner_run(mocker, monkeypatch):  # noqa F811
    mocker.patch.object(openshift_job.OpenshiftJobTestRunner, 'get_token')
    mocker.patch.object(openshift_job.OpenshiftJobTestRunner, 'get_job_template')
    mocker.patch.object(openshift_job.Job, 'create')
    mocker.patch.object(openshift_job.Job, 'wait_on_pod_ready')
    mocker.patch.object(openshift_job.Job, 'get_logs')
    mocker.patch.object(openshift_job.Job, 'cleanup')

    openshift_job.Job.get_logs.return_value = ['log_entry', b'bytes_log_entry']
    monkeypatch.setenv('OCP_API_DOMAIN', 'my_host')
    monkeypatch.setenv('OCP_JOB_NAMESPACE', 'my_project')
    runner = openshift_job.OpenshiftJobTestRunner()
    runner.run()

    assert openshift_job.Job.create.called
    assert openshift_job.Job.wait_on_pod_ready.called
    assert openshift_job.Job.get_logs.called
    assert openshift_job.Job.cleanup.called


def test_runner_get_token(mocker, tmp_path):  # noqa F811
    mocker.patch.object(openshift_job, 'OCP_TOKEN_PATH')
    p = tmp_path / 'session_token'
    p.write_text('my_session_token_1234')
    openshift_job.OCP_TOKEN_PATH = p
    assert openshift_job.OpenshiftJobTestRunner.get_token() == 'my_session_token_1234'


def test_runner_get_job_template(mocker, tmp_path):  # noqa F811
    job_template = openshift_job.OpenshiftJobTestRunner.get_job_template()
    assert job_template.startswith('apiVersion: batch/v1\nkind: Job')


def test_job_init(job):
    assert job.jobs_url == 'my_domain/apis/batch/v1/namespaces/my_ns/jobs'
    assert job.pods_url == 'my_domain/api/v1/namespaces/my_ns/pods'


def test_job_create(mocker, job):  # noqa F811
    mocker.patch.object(requests, 'post')

    requests.post.return_value = SimpleNamespace(status_code=201)
    job.create()
    assert requests.post.called

    requests.post.return_value = SimpleNamespace(status_code=500, reason='', text='')
    with pytest.raises(exc.AnsibleTestError):
        job.create()


def test_job_wait_on_pod_ready(mocker, job):  # noqa F811
    mocker.patch.object(openshift_job.Job, 'get_pods')
    mocker.patch.object(openshift_job.Job, 'cleanup')
    mocker.patch.object(openshift_job, 'POD_CHECK_RETRIES')
    openshift_job.POD_CHECK_RETRIES = 1

    openshift_job.Job.get_pods.return_value = [{'status': {'phase': 'Running'}}]
    job.wait_on_pod_ready()
    assert openshift_job.Job.get_pods.called

    openshift_job.Job.get_pods.return_value = []
    with pytest.raises(exc.AnsibleTestError):
        job.wait_on_pod_ready()
    assert openshift_job.Job.cleanup.called

    openshift_job.Job.get_pods.return_value = [{'status': {'phase': 'Pending'}}]
    with pytest.raises(exc.AnsibleTestError):
        job.wait_on_pod_ready()
    assert openshift_job.Job.cleanup.called


def test_job_get_pods(mocker, job):  # noqa F811
    mocker.patch.object(requests, 'get')
    requests.get.json.return_value = {}
    job.get_pods()
    assert requests.get.called


def test_job_get_pod_name():
    pod = {'metadata': {'name': 'my_pod_name'}}
    assert openshift_job.Job.get_pod_name(pod) == 'my_pod_name'


def test_job_get_logs(mocker, job):  # noqa F811
    mocker.patch.object(openshift_job.Job, 'get_pods')
    mocker.patch.object(requests, 'get')
    openshift_job.Job.get_pods.return_value = [{'metadata': {'name': 'my_pod_name'}}]
    requests.get.iter_lines.return_value = {}
    job.get_logs()
    assert requests.get.called


def test_job_cleanup(mocker, job):  # noqa F811
    mocker.patch.object(openshift_job.Job, 'get_pods')
    mocker.patch.object(requests, 'delete')
    openshift_job.Job.get_pods.return_value = [{'metadata': {'name': 'my_pod_name'}}]
    job.cleanup()
    assert requests.delete.called
