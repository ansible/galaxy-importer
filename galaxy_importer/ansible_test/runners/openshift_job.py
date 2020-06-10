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
API_CHECK_RETRIES = 300
API_CHECK_DELAY_SECONDS = 1
OCP_SERVICEACCOUNT_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/'
IMAGE_BASE_NAME = 'ansible-test'


class OpenshiftJobTestRunner(BaseTestRunner):
    """Run image as an openshift job."""
    def run(self):
        self.log.info('Preparing build and job pod to run ansible-test sanity')
        openshift_build = Build(
            ocp_domain=os.environ['IMPORTER_API_DOMAIN'],
            namespace=os.environ['IMPORTER_JOB_NAMESPACE'],
            session_token=OpenshiftJobTestRunner._get_token(),
            ca_path=OpenshiftJobTestRunner._get_ca_path(),
            archive_url=self._get_pulp_archive_url(self.file),
            build_template=OpenshiftJobTestRunner._get_build_template(),
            logger=self.log,
        )

        image_link = openshift_build.start_and_get_image_link()
        self.log.debug(f'image_link={image_link}')

        job = Job(
            ocp_domain=os.environ['IMPORTER_API_DOMAIN'],
            namespace=os.environ['IMPORTER_JOB_NAMESPACE'],
            session_token=OpenshiftJobTestRunner._get_token(),
            ca_path=OpenshiftJobTestRunner._get_ca_path(),
            image=image_link,
            job_template=OpenshiftJobTestRunner._get_job_template(),
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

        openshift_build.cleanup()
        job.cleanup()

    @staticmethod
    def _get_token():
        with open(os.path.join(OCP_SERVICEACCOUNT_PATH, 'token'), 'r') as f:
            token = f.read().rstrip()
        return token

    @staticmethod
    def _get_ca_path():
        return os.path.join(OCP_SERVICEACCOUNT_PATH, 'ca.crt')

    @staticmethod
    def _get_job_template():
        path = pkg_resources.resource_filename('galaxy_importer', 'ansible_test/job_template.yaml')
        with open(path, 'r') as f:
            job_template = f.read()
        return job_template

    @staticmethod
    def _get_build_template():
        path = pkg_resources.resource_filename(
            'galaxy_importer', 'ansible_test/build_template.yaml')
        with open(path, 'r') as f:
            build_template = f.read()
        return build_template

    @staticmethod
    def _get_pulp_archive_url(pulp_artifact_file):
        parameters = {'ResponseContentDisposition': 'attachment;filename=archive.tar.gz'}
        return pulp_artifact_file.storage.url(pulp_artifact_file.name, parameters=parameters)


class Build(object):
    """Interact with Openshift builds via REST API."""
    def __init__(self, ocp_domain, namespace, session_token,
                 ca_path, build_template, archive_url, logger):
        self.name = 'import-' + str(uuid.uuid4())
        self.auth_header = {'Authorization': f'Bearer {session_token}'}
        self.ca_path = ca_path
        self.api_build_prefix = f'{ocp_domain}/apis/build.openshift.io/v1/namespaces/{namespace}'
        self.buildconfig_url = f'{self.api_build_prefix}/buildconfigs'
        self.build_url = f'{self.api_build_prefix}/builds'
        self.istag_url = \
            f'{ocp_domain}/apis/image.openshift.io/v1/namespaces/{namespace}/imagestreamtags'
        self.image_name = f'{IMAGE_BASE_NAME}:{self.name}'
        self.build_yaml = build_template.format(
            image_name=self.image_name,
            build_name=self.name,
            download_url=archive_url,
        )
        self.log = logger or default_logger

    def start_and_get_image_link(self):
        self._create_buildconfig()

        self._wait_until_build_created()
        self._wait_until_build_complete()
        self._wait_until_image_available()

        imagestream_tag = self._get_image()
        return imagestream_tag['metadata']['name']

    def _create_buildconfig(self):
        self.log.info(f'Creating buildconfig {self.name}')
        r = requests.post(
            self.buildconfig_url,
            headers=self.auth_header,
            json=yaml.safe_load(self.build_yaml),
            verify=self.ca_path,
        )
        if r.status_code != requests.codes.created:
            raise exceptions.AnsibleTestError(
                f'Could not create buildconfig: {r.status_code} {r.reason} {r.text}')

    def _get_build(self):
        """Get build associated with buildconfig."""
        params = {'labelSelector': f'buildconfig={self.name}'}
        r = requests.get(
            self.build_url, headers=self.auth_header, params=params, verify=self.ca_path)
        if r.status_code != requests.codes.ok:
            raise exceptions.AnsibleTestError('Could not access builds')
        return r.json()

    def _get_image(self):
        """Get imagestream tag associated with buildconfig."""
        r = requests.get(
            '{}/{}'.format(self.istag_url, self.image_name),
            headers=self.auth_header,
            verify=self.ca_path)
        if r.status_code != requests.codes.ok:
            return None
        return r.json()

    def _wait_until_build_created(self):
        self.log.info('Creating build...')
        for i in range(API_CHECK_RETRIES):
            build = self._get_build()
            if len(build['items']) > 0:
                return
            time.sleep(API_CHECK_DELAY_SECONDS)

        raise exceptions.AnsibleTestError('Could not create build')

    def _wait_until_build_complete(self):
        self.log.info('Waiting until build is complete...')
        for i in range(API_CHECK_RETRIES):
            build = self._get_build()
            build_phase = build['items'][0]['status']['phase']
            if build_phase == 'Complete':
                return
            time.sleep(API_CHECK_DELAY_SECONDS)

        raise exceptions.AnsibleTestError('Unable to build image within timeout')

    def _wait_until_image_available(self):
        self.log.info('Waiting until image is available...')
        for i in range(API_CHECK_RETRIES):
            if self._get_image():
                return
            time.sleep(API_CHECK_DELAY_SECONDS)
        raise exceptions.AnsibleTestError('Image was not available')

    def _delete_buildconfig(self):
        r = requests.delete(
            '{}/{}'.format(self.buildconfig_url, self.name),
            headers=self.auth_header,
            verify=self.ca_path)
        self.log.debug(f'delete bc: {r.status_code} {r.reason} {r.text}')

    def _delete_imagestreamtag(self):
        r = requests.delete(
            '{}/{}'.format(self.istag_url, self.image_name),
            headers=self.auth_header,
            verify=self.ca_path)
        self.log.debug(f'delete istag: {r.status_code} {r.reason} {r.text}')

    def cleanup(self):
        self._delete_buildconfig()
        self._delete_imagestreamtag()


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
            memory_request=os.environ.get('IMPORTER_MEMORY_REQUEST', '256Mi'),
            memory_limit=os.environ.get('IMPORTER_MEMORY_LIMIT', '1Gi'),
            cpu_request=os.environ.get('IMPORTER_CPU_REQUEST', '500m'),
            cpu_limit=os.environ.get('IMPORTER_CPU_LIMIT', '500m'),
            job_timeout=os.environ.get('IMPORTER_JOB_TIMEOUT', '900'),
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
        for i in range(API_CHECK_RETRIES):
            pods = self.get_pods()
            if len(pods) < 1:
                time.sleep(API_CHECK_DELAY_SECONDS)
                continue
            break

        if len(pods) < 1:
            self.cleanup()
            raise exceptions.AnsibleTestError('Could not create pod associated with job')

        self.log.info('Scheduling pod and waiting until it is running...')
        for i in range(API_CHECK_RETRIES):
            pods = self.get_pods()
            pod_phase = pods[0]['status']['phase']
            if pod_phase != 'Pending':
                return
            time.sleep(API_CHECK_DELAY_SECONDS)

        self.log.debug(pods[0]['status'])
        self.cleanup()
        raise exceptions.AnsibleTestError('Could not start pod associated with job')

    def get_pods(self):
        """Get pods associated with job."""
        params = {'labelSelector': f'job-name={self.name}'}
        r = requests.get(
            self.pods_url, headers=self.auth_header, params=params, verify=self.ca_path)
        try:
            pods = r.json()['items']
        except (KeyError, ValueError):
            raise exceptions.AnsibleTestError('Could not access pod assocated with job')
        return pods

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
        requests.delete(self.job_name_url, headers=self.auth_header, verify=self.ca_path)
        self.log.debug(f'Deleted job {self.name}')

        for pod in self.get_pods():
            pod_name = self.get_pod_name(pod)
            requests.delete(
                f'{self.pods_url}/{pod_name}', headers=self.auth_header, verify=self.ca_path)
            self.log.debug(f'Deleted pod {pod_name}')

            status = pod['status']['phase']
            if status == 'Failed':
                reason = pod['status']['containerStatuses'][0]['state']['terminated']['reason']
                raise exceptions.AnsibleTestError(
                    f'Pod terminated with status: "{status}" and reason: "{reason}"')
