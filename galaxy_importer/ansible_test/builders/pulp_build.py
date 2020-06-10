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
import subprocess
import time
import uuid

from galaxy_importer import config
from galaxy_importer import constants
from galaxy_importer import exceptions
from shutil import copy, copyfile, copyfileobj

default_logger = logging.getLogger(__name__)
config_data = config.ConfigFile.load()
cfg = config.Config(config_data=config_data)
API_CHECK_RETRIES = 360
API_CHECK_DELAY_SECONDS = 1


class Build(object):
    """Use pulp-container to build ansible-test image with artifact inside."""
    def __init__(self, pulp_artifact_file, api_url, content_url, metadata, logger):
        self.api_url = api_url
        self.content_url = content_url
        self.basic_auth = ('admin', 'admin')
        self.pulp_artifact_file = pulp_artifact_file
        self.metadata = metadata
        self.shared_dockerfile = os.path.join(
            os.path.dirname(constants.ROOT_DIR.rstrip('galaxy_importer')),
            'docker/ansible-test/Dockerfile')
        self.dockerfile = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'Dockerfile')
        self.collection_file = self._get_collection_file()
        self.registry_base_path = 'galaxy-importer'
        self.registry_name = 'archive-test'
        self.log = logger or default_logger
        self.setup_dockerfile()

    def _get_collection_file(self):
        path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'archive.tar.bz')
        try:
            url = Build._get_pulp_archive_url(self.pulp_artifact_file)
            with requests.get(url, stream=True) as r:
                with open(path, 'wb') as f:
                    copyfileobj(r.raw, f)
        except AttributeError:
            spath = os.path.join(
                os.path.dirname(constants.ROOT_DIR.rstrip('galaxy_importer')),
                f'{self.metadata.namespace}-{self.metadata.name}-{self.metadata.version}.tar.gz')
            path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'archive.tar.gz')
            copy(spath, path)
        return path

    def setup_dockerfile(self):
        # Make a copy of Dockerfile
        copyfile(
            self.shared_dockerfile,
            self.dockerfile)

        # Update Dockerfile to download and copy Collection into the image.
        with open(self.dockerfile, 'a') as f:
            f.write("\nCOPY archive.tar.gz /archive/archive.tar.gz\n")

    def build(self):
        self.container_repository_href = self._get_container_repository_href()
        self.dockerfile_artifact_href = self._get_artifact_href(self.dockerfile)
        self.collection_artifact_href = self._get_artifact_href(self.collection_file)
        self.container_distribution_href = self._get_container_distribution_href()
        self._build_image()

    def get_registry_href(self):
        return self._get_registry_href()

    def _build_image(self):
        artifacts = json.dumps({f'{self.collection_artifact_href}': 'archive.tar.gz'})
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
            self.log.info('Building image...')
            status = r.json()['state']
            if status == 'failed' or status == 'canceled':
                self.cleanup()
                raise exceptions.AnsibleTestError(
                    f'Could not create image: \
                        {r.status_code} {r.reason} {r.text}')
            elif status == 'completed':
                self.log.info('Image successfully built')
                return
            time.sleep(API_CHECK_DELAY_SECONDS)
        if i >= API_CHECK_DELAY_SECONDS:
            self.cleanup()
            raise exceptions.AnsibleTestError('Timed out building image')

    def _get_artifact_href(self, f):
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
        r = requests.post(
            url=f'{self.api_url}/pulp/api/v3/repositories/container/container/',
            auth=self.basic_auth,
            json={'name': f'ansible_test_repo_{str(uuid.uuid4())}'}
        )
        if r.status_code != 201:
            raise exceptions.AnsibleTestError(
                f'Could not create ContainerRepository: \
                    {r.status_code} {r.reason} {r.text}')
        return r.json()['pulp_href']

    def _get_container_distribution_href(self):
        pulp_url = '/pulp/api/v3/distributions/container/container/'
        r = requests.post(
            url=f'{self.api_url}{pulp_url}',
            auth=self.basic_auth,
            json={
                'name': self.registry_name,
                'base_path': self.registry_base_path,
                'repository': self.container_repository_href
            }
        )
        if r.status_code == 202:
            return self._wait_for_dist_build(r.json()['task'])
        else:
            raise exceptions.AnsibleTestError(
                f'Could not create ContainerDistribution: \
                    {r.status_code} {r.reason} {r.text}')

    def _wait_for_dist_build(self, task_href):
        for i in range(API_CHECK_RETRIES):
            r = requests.get(
                url=f'{self.api_url}{task_href}',
                auth=self.basic_auth)
            status = r.json()['state']
            if status == 'failed' or status == 'canceled':
                self.cleanup()
                raise exceptions.AnsibleTestError(
                    f'Could not create ContainerDistribution: \
                        {r.status_code} {r.reason} {r.text}')
            elif status == 'completed':
                return r.json()['created_resources'][0]
            time.sleep(API_CHECK_DELAY_SECONDS)

    def _get_registry_href(self):
        r = requests.get(
            url=f'{self.api_url}{self.container_distribution_href}',
            auth=self.basic_auth,
        )
        if r.status_code == 200:
            self._add_registry_to_conf(r.json()['registry_path'])
            return r.json()['registry_path']
        else:
            raise exceptions.AnsibleTestError(
                f'Could not retrieve Registry href: \
                    {r.status_code} {r.reason} {r.text}')

    def _add_registry_to_conf(self, registry_href):
        reg_file = f'/home/{os.getlogin()}/.config/containers/registries.conf'
        if not os.path.exists(reg_file):
            path = f'home/{os.getlogin()}/.config/containers'.split('/')
            for index, item in enumerate(path):
                current_path = Build._get_current_path(index, path)
                if not os.path.exists(current_path):
                    subprocess.run(['mkdir', f'{current_path}'])
                else:
                    continue
            subprocess.run(['touch', f'{reg_file}'])

        with open(reg_file, 'r+') as f:
            if os.stat(reg_file).st_size == 0:
                c = '[registries.insecure]\n'
                c = c + f'registries = ["{registry_href}"]'
            else:
                c = f.readlines()
                for index, line in enumerate(c):
                    if 'registries = [' in line and registry_href not in line:
                        c[index] = line.replace(
                            'registries = [',
                            f"registries = ['{registry_href}', ")
            f.seek(0)
            f.truncate()
            f.writelines(c)

    @staticmethod
    def _get_current_path(index, path):
        d = ''
        i = 0
        while i <= index:
            d = d + f'/{path[i]}'
            i = i + 1
        return d

    def cleanup(self):
        """Clean up temporary data structures and files"""
        self._delete_container_repository(self.container_repository_href)
        self._delete_container_distribution(self.container_distribution_href)
        self._delete_artifact(self.dockerfile_artifact_href)
        self._delete_artifact(self.collection_artifact_href)
        os.remove(self.dockerfile)
        os.remove(self.collection_file)

    def _delete_container_repository(self, repository_href):
        r = requests.delete(
            f'{self.api_url}{repository_href}',
            auth=self.basic_auth)
        if r.status_code != 202:
            raise exceptions.AnsibleTestError(
                f'Could not delete ContainerRepository: \
                    {r.status_code} {r.reason} {r.text}')

    def _delete_container_distribution(self, distribution_href):
        r = requests.delete(
            f'{self.api_url}{distribution_href}',
            auth=self.basic_auth)
        if r.status_code != 202:
            raise exceptions.AnsibleTestError(
                f'Could not delete ContainerDistribution: \
                    {r.status_code} {r.reason} {r.text}')

    def _delete_artifact(self, artifact_href):
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
