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

import json
import logging
import os
import requests
import time
import uuid

from galaxy_importer import config
from galaxy_importer import constants
from galaxy_importer import exceptions
from shutil import copyfile

default_logger = logging.getLogger(__name__)
config_data = config.ConfigFile.load()
cfg = config.Config(config_data=config_data)
API_CHECK_RETRIES = 300
API_CHECK_DELAY_SECONDS = 1


class Build(object):
    """Use pulp-container to build ansible-test image with artifact inside."""
    def __init__(self, pulp_artifact_file, logger):
        self.api_url = 'http://localhost:8080'
        self.basic_auth = ('admin', 'admin')
        self.pulp_artifact_file = pulp_artifact_file
        self.shared_dockerfile = os.path.join(
            os.path.dirname(constants.ROOT_DIR.rstrip('galaxy_importer')),
            'docker/ansible-test/Dockerfile')
        self.dockerfile = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'Dockerfile')
        self.collection_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'archive.tar.gz')
        self.log = logger or default_logger
        self.setup_dockerfile()

    def setup_dockerfile(self):
        # Make a copy of shared Dockerfile
        # copyfile(
        #     self.shared_dockerfile,
        #     self.dockerfile)

        # Update Dockerfile to download and copy Collection into the image.
        with open(self.dockerfile, 'r+') as f:
            content = f.readlines()
            for index, line in enumerate(content):
                if 'apt-get install -y wget' in line:
                    content.insert(
                        index - 2,
                        "\nCOPY archive.tar.gz /archive/archive.tar.gz\n")
                    # ^ local dev only
                    # content.insert(
                    #   index + 1,
                    #   f'    && wget -O archive.tar.gz {self._get_pulp_archive_url(pulp_artifact_file)} \\\n')
                    break
            f.seek(0)
            f.truncate()
            f.writelines(content)

    def build(self):
        self.log.info('Creating ContainerRepository')
        self.container_repository_href = self._get_container_repository_href()

        self.log.info('Creating Dockerfile Artifact')
        self.dockerfile_artifact_href = self._get_artifact_href(
            self.dockerfile)
        self.log.info(f'Dockerfile Artifact: {self.dockerfile_artifact_href}')

        self.log.info('Creating Collection Artifact')
        self.collection_artifact_href = self._get_artifact_href(
            self.collection_file)
        self.log.info(f'Collection Artifact: {self.collection_artifact_href}')

        self._build_image()

        self.log.info('Creating ContainerDistribution')
        self.container_distribution_href = self._get_container_distribution_href()

        return f'{self.api_url}{self.container_distribution_href}'

    def _build_image(self):
        self.log.info(
            f'Building image with {self.pulp_artifact_file.name} embedded.')
        artifacts = json.dumps(
            {f'{self.collection_artifact_href}': 'archive.tar.gz'})
        r = requests.post(
            url=f'{self.api_url}{self.container_repository_href}build_image/',
            auth=self.basic_auth,
            data={
                'containerfile_artifact': self.dockerfile_artifact_href,
                # 'containerfile': open(self.dockerfile, 'rb'),
                'tag': 'latest',
                'artifacts': artifacts
            }
            # files={'containerfile': open(self.dockerfile, 'rb')}
        )
        if r.status_code != 202:
            self.cleanup()
            raise exceptions.AnsibleTestError(
                f'Could not build Image: {r.status_code} {r.reason} {r.text}')
        return self._wait_for_image_build(r.json()['task'])

    def _wait_for_image_build(self, task_href):
        for i in range(API_CHECK_RETRIES):
            r = requests.get(
                url=f'{self.api_url}{task_href}',
                auth=self.basic_auth)
            self.log.info('building image...')
            status = r.json()['state']
            if status == 'failed' or status == 'canceled':
                self.cleanup()
                raise exceptions.AnsibleTestError(
                    f'Could not create image: \
                        {r.status_code} {r.reason} {r.text}')
            elif status == 'completed':
                self.log.info('Image successfully built')
                break
            time.sleep(API_CHECK_DELAY_SECONDS)

    def _get_artifact_href(self, f):
        """Creates a Pulp Artifact with passed in file and returns pulp_href"""
        r = requests.post(
            url=f'{self.api_url}/pulp/api/v3/artifacts/',
            auth=self.basic_auth,
            files={'file': open(f, 'rb')}
        )
        if r.status_code != 201:
            raise exceptions.AnsibleTestError(
                f'Could not create Artifact: \
                    {r.status_code} {r.reason} {r.text}')
        return r.json()['pulp_href']

    def _get_container_repository_href(self):
        """Create a Pulp ContainerRepository and return the href to it."""
        repo_name = f'ansible_test_repo_{str(uuid.uuid4())}'
        r = requests.post(
            url=f'{self.api_url}/pulp/api/v3/repositories/container/container/',
            auth=self.basic_auth,
            json={'name': repo_name}
        )
        if r.status_code != 201:
            raise exceptions.AnsibleTestError(
                f'Could not create ContainerRepository: \
                    {r.status_code} {r.reason} {r.text}')
        return r.json()['pulp_href']

    def _get_container_distribution_href(self):
        r = requests.post(
            url=f'{self.api_url}/pulp/api/v3/distributions/container/container/',
            auth=self.basic_auth,
            json={
                'name': f'ansible_test_dist_name_{str(uuid.uuid4())}',
                'base_path': f'ansible-test_base_path_{str(uuid.uuid4())}',
                'repository': self.container_repository_href
            }
        )
        if r.status_code != 202:
            raise exceptions.AnsibleTestError(
                f'Could not create ContainerDistribution: \
                    {r.status_code} {r.reason} {r.text}')
        else:
            return self._wait_for_dist_build(r.json()['task'])

    def _wait_for_dist_build(self, task_href):
        for i in range(API_CHECK_RETRIES):
            r = requests.get(
                url=f'{self.api_url}{task_href}',
                auth=self.basic_auth)
            self.log.info(f'building distribution...')
            status = r.json()['state']
            if status == 'failed' or status == 'canceled':
                self.cleanup()
                raise exceptions.AnsibleTestError(
                    f'Could not create ContainerDistribution: \
                        {r.status_code} {r.reason} {r.text}')
            elif status == 'completed':
                self.log.info(f'Distribution successfully built:\n {r.json()}')
                return f"{r.json()['created_resources'][0]}"
            time.sleep(API_CHECK_DELAY_SECONDS)

    def cleanup(self):
        """Clean up temporary data structures"""
        self.log.info('Removing temporary data structures')
        self._delete_container_repository(self.container_repository_href)
        self._delete_container_distribution(self.container_distribution_href)
        self._delete_artifact(self.dockerfile_artifact_href)
        self._delete_artifact(self.collection_artifact_href)
        # os.remove(self.dockerfile)
        # os.remove(self.collection_file)

    def _delete_container_repository(self, repository_href):
        """Delete the supplied ContainerRepository."""
        self.log.debug('Deleting ContainerRepository')
        r = requests.delete(
            f'{self.api_url}{repository_href}',
            auth=self.basic_auth)
        if r.status_code != 202:  # returns task
            raise exceptions.AnsibleTestError(
                f'Could not delete ContainerRepository: \
                    {r.status_code} {r.reason} {r.text}')

    def _delete_container_distribution(self, distribution_href):
        """Delete the supplied ContainerDistribution."""
        self.log.debug('Deleting ContainerDistribution')
        r = requests.delete(
            f'{self.api_url}{distribution_href}',
            auth=self.basic_auth)
        if r.status_code != 202:  # returns task
            raise exceptions.AnsibleTestError(
                f'Could not delete ContainerDistribution: \
                    {r.status_code} {r.reason} {r.text}')

    def _delete_artifact(self, artifact_href):
        """Delete the supplied Artifact"""
        self.log.debug(f'Deleting Dockerfile Artifact')
        r = requests.delete(
            f'{self.api_url}{artifact_href}',
            auth=self.basic_auth)
        if r.status_code != 204:
            raise exceptions.AnsibleTestError(
                f'Could not delete Dockerfile Artifact: \
                    {r.status_code} {r.reason} {r.text}')

    @staticmethod
    def _get_pulp_archive_url(pulp_artifact_file):
        parameters = {
            'ResponseContentDisposition': 'attachment;filename=archive.tar.gz'
        }
        return pulp_artifact_file.storage.url(
            pulp_artifact_file.name,
            parameters=parameters)
