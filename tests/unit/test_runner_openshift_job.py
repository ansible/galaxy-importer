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
import requests

from galaxy_importer import exceptions as exc
from galaxy_importer.ansible_test.runners import openshift_job


@pytest.fixture
def job():
    return openshift_job.Job(
        'my_domain', 'my_ns', 'session_token', 'ca_path', 'image', 'job_template', logger=None)


@pytest.fixture
def build():
    return openshift_job.Build(
        'my_domain', 'my_ns', 'session_token', 'ca_path',
        'build_template', 'archive_url', logger=None)


def test_runner_run(mocker, monkeypatch):
    mocker.patch.object(openshift_job.OpenshiftJobTestRunner, '_get_token')
    mocker.patch.object(openshift_job.OpenshiftJobTestRunner, '_get_job_template')
    mocker.patch.object(openshift_job.OpenshiftJobTestRunner, '_get_pulp_archive_url')
    mocker.patch.object(openshift_job.Job, 'create')
    mocker.patch.object(openshift_job.Job, 'wait_on_pod_ready')
    mocker.patch.object(openshift_job.Job, 'get_logs')
    mocker.patch.object(openshift_job.Job, 'cleanup')
    mocker.patch.object(openshift_job.Build, 'start_and_get_image_link')
    mocker.patch.object(openshift_job.Build, 'cleanup')

    openshift_job.Job.get_logs.return_value = ['log_entry', b'bytes_log_entry']
    openshift_job.OpenshiftJobTestRunner._get_pulp_archive_url.return_value = 'image_link'
    monkeypatch.setenv('IMPORTER_API_DOMAIN', 'my_host')
    monkeypatch.setenv('IMPORTER_JOB_NAMESPACE', 'my_project')
    runner = openshift_job.OpenshiftJobTestRunner()
    runner.run()

    assert openshift_job.Build.start_and_get_image_link.called
    assert openshift_job.Job.create.called
    assert openshift_job.Job.wait_on_pod_ready.called
    assert openshift_job.Job.get_logs.called
    assert openshift_job.Job.cleanup.called
    assert openshift_job.Build.cleanup.called


def test_runner_get_token(mocker, tmp_path):
    mocker.patch.object(openshift_job, 'OCP_SERVICEACCOUNT_PATH')
    p = tmp_path / 'token'
    p.write_text('my_session_token_1234')
    openshift_job.OCP_SERVICEACCOUNT_PATH = str(tmp_path) + '/'
    assert openshift_job.OpenshiftJobTestRunner._get_token() == 'my_session_token_1234'


def test_runner_get_job_template(mocker, tmp_path):
    job_template = openshift_job.OpenshiftJobTestRunner._get_job_template()
    assert job_template.startswith('apiVersion: batch/v1\nkind: Job')


def test_job_init(job):
    assert job.jobs_url == 'my_domain/apis/batch/v1/namespaces/my_ns/jobs'
    assert job.pods_url == 'my_domain/api/v1/namespaces/my_ns/pods'


def test_job_create(mocker, job):
    mocker.patch.object(requests, 'post')

    requests.post.return_value = SimpleNamespace(status_code=201)
    job.create()
    assert requests.post.called

    requests.post.return_value = SimpleNamespace(status_code=500, reason='', text='')
    with pytest.raises(exc.AnsibleTestError):
        job.create()


def test_job_wait_on_pod_ready(mocker, job):
    mocker.patch.object(openshift_job.Job, 'get_pods')
    mocker.patch.object(openshift_job.Job, 'cleanup')
    mocker.patch.object(openshift_job, 'API_CHECK_RETRIES')
    openshift_job.API_CHECK_RETRIES = 1

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


def test_job_get_pods(mocker, job):
    mocker.patch.object(requests, 'get')
    requests.get.return_value.json.return_value = {'items': []}
    job.get_pods()
    assert requests.get.called


def test_job_get_pods_fail(mocker, job):
    mocker.patch.object(requests, 'get')
    requests.get.return_value.json.return_value = {}
    with pytest.raises(exc.AnsibleTestError, match=r'Could not access pod assocated with job'):
        job.get_pods()
    assert requests.get.called


def test_job_get_pod_name():
    pod = {'metadata': {'name': 'my_pod_name'}}
    assert openshift_job.Job.get_pod_name(pod) == 'my_pod_name'


def test_job_get_logs(mocker, job):
    mocker.patch.object(openshift_job.Job, 'get_pods')
    mocker.patch.object(requests, 'get')
    openshift_job.Job.get_pods.return_value = [{'metadata': {'name': 'my_pod_name'}}]
    requests.get.iter_lines.return_value = {}
    job.get_logs()
    assert requests.get.called


def test_job_cleanup(mocker, job):
    mocker.patch.object(openshift_job.Job, 'get_pods')
    mocker.patch.object(requests, 'delete')
    openshift_job.Job.get_pods.return_value = [{
        'metadata': {'name': 'my_pod_name'},
        'status': {'phase': 'Succeeded'},
    }]
    job.cleanup()
    assert requests.delete.called


def test_job_cleanup_fail(mocker, job):
    mocker.patch.object(openshift_job.Job, 'get_pods')
    mocker.patch.object(requests, 'delete')
    openshift_job.Job.get_pods.return_value = [{
        'metadata': {'name': 'my_pod_name'},
        'status': {
            'phase': 'Failed',
            'containerStatuses': [
                {'state': {'terminated': {'reason': 'internal_error_123'}}}
            ]
        },
    }]
    with pytest.raises(
        exc.AnsibleTestError,
        match=r'Pod terminated with status: "Failed" and reason: "internal_error_123"'
    ):
        job.cleanup()
    assert requests.delete.called


def test_build_create_buildconfig(mocker, build):
    mocker.patch.object(requests, 'post')

    requests.post.return_value = SimpleNamespace(status_code=201)
    build._create_buildconfig()
    assert requests.post.called

    requests.post.return_value = SimpleNamespace(status_code=500, reason='', text='')
    with pytest.raises(exc.AnsibleTestError):
        build._create_buildconfig()


def test_job_get_build(mocker, build):
    mocker.patch.object(requests, 'get')

    requests.get.return_value = SimpleNamespace(status_code=200, json=lambda: {'func': 'result'})
    assert build._get_build() == {'func': 'result'}

    requests.get.return_value = SimpleNamespace(status_code=500, reason='', text='')
    with pytest.raises(exc.AnsibleTestError):
        build._get_build()


def test_job_get_image(mocker, build):
    mocker.patch.object(requests, 'get')

    requests.get.return_value = SimpleNamespace(status_code=200, json=lambda: {'func': 'result'})
    assert build._get_image() == {'func': 'result'}

    requests.get.return_value = SimpleNamespace(status_code=500)
    assert build._get_image() is None


def test_runner_get_build_template(mocker, tmp_path):
    build_template = openshift_job.OpenshiftJobTestRunner._get_build_template()
    assert build_template.startswith('apiVersion: build.openshift.io/v1\nkind: BuildConfig')


def test_wait_until_build_created(mocker, build):
    mocker.patch.object(openshift_job.Build, '_get_build')
    mocker.patch.object(openshift_job, 'API_CHECK_RETRIES')
    openshift_job.API_CHECK_RETRIES = 1

    openshift_job.Build._get_build.return_value = {'items': ['item']}
    build._wait_until_build_created()

    openshift_job.Build._get_build.return_value = {'items': []}
    with pytest.raises(exc.AnsibleTestError):
        build._wait_until_build_created()


def test_wait_until_build_complete(mocker, build):
    mocker.patch.object(openshift_job.Build, '_get_build')
    mocker.patch.object(openshift_job, 'API_CHECK_RETRIES')
    openshift_job.API_CHECK_RETRIES = 1

    openshift_job.Build._get_build.return_value = {'items': [{'status': {'phase': 'Complete'}}]}
    build._wait_until_build_complete()

    openshift_job.Build._get_build.return_value = {'items': [{'status': {'phase': 'Pending'}}]}
    with pytest.raises(exc.AnsibleTestError):
        build._wait_until_build_complete()


def test_wait_until_image_available(mocker, build):
    mocker.patch.object(openshift_job.Build, '_get_image')
    mocker.patch.object(openshift_job, 'API_CHECK_RETRIES')
    openshift_job.API_CHECK_RETRIES = 1

    openshift_job.Build._get_image.return_value = 'image_link'
    build._wait_until_image_available()

    openshift_job.Build._get_image.return_value = None
    with pytest.raises(exc.AnsibleTestError):
        build._wait_until_image_available()


def test_delete_buildconfig(mocker, build):
    mocker.patch.object(requests, 'delete')
    requests.delete.return_value = SimpleNamespace(status_code=204, reason='', text='')
    build._delete_buildconfig()
    assert requests.delete.called


def test_delete_imagestreamtag(mocker, build):
    mocker.patch.object(requests, 'delete')
    requests.delete.return_value = SimpleNamespace(status_code=204, reason='', text='')
    build._delete_imagestreamtag()
    assert requests.delete.called


def test_build_cleanup(mocker, build):
    mocker.patch.object(openshift_job.Build, '_delete_buildconfig')
    mocker.patch.object(openshift_job.Build, '_delete_imagestreamtag')
    mocker.patch.object(requests, 'delete')
    build.cleanup()
    assert openshift_job.Build._delete_buildconfig.called
    assert openshift_job.Build._delete_imagestreamtag.called


def test_build_start_and_get_image_link(mocker, build):
    mocker.patch.object(openshift_job.Build, '_create_buildconfig')
    mocker.patch.object(openshift_job.Build, '_wait_until_build_created')
    mocker.patch.object(openshift_job.Build, '_wait_until_build_complete')
    mocker.patch.object(openshift_job.Build, '_wait_until_image_available')
    mocker.patch.object(openshift_job.Build, '_get_image')
    openshift_job.Build._get_image.return_value = {
        'metadata': {'name': 'image_stream_tag_name'}}
    assert build.start_and_get_image_link() == 'image_stream_tag_name'
    assert openshift_job.Build._create_buildconfig.called
    assert openshift_job.Build._wait_until_build_created.called
    assert openshift_job.Build._wait_until_build_complete.called
    assert openshift_job.Build._wait_until_image_available.called
