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


import logging
import os
import pkg_resources
import requests
import time
import uuid
import yaml

from galaxy_importer import config
from galaxy_importer import exceptions
from galaxy_importer.ansible_test.runners.base import BaseTestRunner


default_logger = logging.getLogger(__name__)

cfg = config.Config()
POD_CHECK_RETRIES = 200  # TODO: try to shorten once not pulling image from quay
POD_CHECK_DELAY_SECONDS = 1
OCP_SERVICEACCOUNT_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/'
TEMP_IMG_WITH_ARCHIVE = 'quay.io/awcrosby/ans-test-with-archive'


class OpenshiftJobTestRunner(BaseTestRunner):
    """Run image as an openshift job."""
    def run(self):
        # TODO: change from temp image to build image with pulp-container
        # image = container_build.build_image_with_artifact()
        image = TEMP_IMG_WITH_ARCHIVE

        job = Job(
            ocp_domain=os.environ['IMPORTER_API_DOMAIN'],
            namespace=os.environ['IMPORTER_JOB_NAMESPACE'],
            session_token=OpenshiftJobTestRunner.get_token(),
            ca_path=OpenshiftJobTestRunner.get_ca_path(),
            image=image,
            job_template=OpenshiftJobTestRunner.get_job_template(),
            logger=self.log,
        )
        job.create()
        job.wait_on_pod_ready()
        iter_logs = job.get_logs()

        for line in iter_logs:
            if isinstance(line, bytes):
                self.log.error('Unexpected bytes in logs: {}'.format(str(line)))
                continue
            self.log.info(line)

        job.cleanup()

    @staticmethod
    def get_token():
        with open(os.path.join(OCP_SERVICEACCOUNT_PATH, 'token'), 'r') as f:
            token = f.read().rstrip()
        return token

    @staticmethod
    def get_ca_path():
        return os.path.join(OCP_SERVICEACCOUNT_PATH, 'ca.crt')

    @staticmethod
    def get_job_template():
        path = pkg_resources.resource_filename('galaxy_importer', 'ansible_test/job_template.yaml')
        with open(path, 'r') as f:
            job_template = f.read()
        return job_template


class Job(object):
    """Interact with Openshift Job via REST API."""

    def __init__(self, ocp_domain, namespace, session_token, ca_path, image, job_template, logger):
        self.name = 'ansible-test-' + str(uuid.uuid4())
        self.auth_header = {'Authorization': f'Bearer {session_token}'}
        self.ca_path = ca_path
        self.jobs_url = f'{ocp_domain}/apis/batch/v1/namespaces/{namespace}/jobs'
        self.job_name_url = f'{self.jobs_url}/{self.name}'
        self.pods_url = f'{ocp_domain}/api/v1/namespaces/{namespace}/pods'
        self.pod_url_template = '{pods_url}/{pod_name}'
        self.log_url_template = '{pods_url}/{pod_name}/log'
        self.job_yaml = job_template.format(
            job_name=self.name,
            image=image,
        )
        self.log = logger or default_logger

    def create(self):
        """Create the job."""

        self.log.info(f'Creating job {self.name}')
        r = requests.post(
            self.jobs_url,
            headers=self.auth_header,
            json=yaml.safe_load(self.job_yaml),
            verify=self.ca_path,
        )
        if r.status_code != requests.codes.created:
            raise exceptions.AnsibleTestError(
                f'Could not create job: {r.status_code} {r.reason} {r.text}')

    def wait_on_pod_ready(self):
        """Wait until job's pod initializes, pulls image, and starts running."""

        self.log.info('Creating pod...')
        for i in range(POD_CHECK_RETRIES):
            pods = self.get_pods()
            if len(pods) < 1:
                time.sleep(POD_CHECK_DELAY_SECONDS)
                continue
            break

        if len(pods) < 1:
            self.cleanup()
            raise exceptions.AnsibleTestError('Could not create pod assocated with job')

        self.log.info('Scheduling pod and waiting until it is running...')
        for i in range(POD_CHECK_RETRIES):
            pods = self.get_pods()
            pod_phase = pods[0]['status']['phase']
            if pod_phase != 'Pending':
                return
            time.sleep(POD_CHECK_DELAY_SECONDS)

        self.log.debug(pods[0]['status'])
        self.cleanup()
        raise exceptions.AnsibleTestError('Could not start pod assocated with job')

    def get_pods(self):
        """Get pods associated with job."""
        params = {'labelSelector': f'job-name={self.name}'}
        r = requests.get(
            self.pods_url, headers=self.auth_header, params=params, verify=self.ca_path)
        return r.json()['items']

    @staticmethod
    def get_pod_name(pod):
        return pod['metadata']['name']

    def get_logs(self):
        """Returns stream of lines from the logs of the pod."""
        pod = self.get_pods()[0]
        pod_name = self.get_pod_name(pod)
        r = requests.get(
                url=f'{self.pods_url}/{pod_name}/log',
                headers=self.auth_header,
                params=dict(follow='true'),
                verify=self.ca_path,
                stream=True,
            )
        return r.iter_lines(decode_unicode=True)

    def cleanup(self):
        """Deletes job and any pods associated to it."""
        pod_names = [self.get_pod_name(pod) for pod in self.get_pods()]
        requests.delete(self.job_name_url, headers=self.auth_header, verify=self.ca_path)
        self.log.debug(f'Deleted job {self.name}')
        for pod_name in pod_names:
            requests.delete(
                f'{self.pods_url}/{pod_name}', headers=self.auth_header, verify=self.ca_path)
            self.log.debug(f'Deleted pod {pod_name}')
