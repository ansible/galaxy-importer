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
import subprocess

from galaxy_importer.ansible_test.runners.base import BaseTestRunner
from galaxy_importer.ansible_test.builders.pulp_build import Build
from galaxy_importer.ansible_test.builders.pulp import PulpServer

default_logger = logging.getLogger(__name__)


class LocalImageTestRunner(BaseTestRunner):
    """Run image locally with docker or podman."""
    def run(self):
        self.log.info('Preparing pulp-container build environment')
        pulp = PulpServer(logger=self.log)
        pulp.start()

        pulp_container_build = Build(
            api_url=pulp.get_api_url(),
            pulp_artifact_file=self.file,
            logger=self.log,
        )

        # Build OCI ansible-test image and retrieve link to it
        self.log.info('Building ansible-test image..')
        pulp_container_build.build()

        self.log.info('Retrieving Pulp Registry address..')
        registry_href = pulp_container_build.get_registry_href()
        self.log.info(f'registry_href: {registry_href}')

        # Run ansible-test image via Podman
        self.pull_image(registry_href)

        # Capture ansible-test output

        # Cleanup ContainerRepository, Artifacts, Dockerfile and Image
        pulp_container_build.cleanup()
        pulp.cleanup()

    # TODO add registry to /etc/containers/registries.conf

    def pull_image(self, registry_href):
        registry = registry_href.lstrip('http://')
        cmd = ['podman', 'pull', '--tls-verify=false', registry]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
        )
        return_code = proc.wait()
        if return_code == 0:
            self.run_image()
        else:
            self.log.error(
                'An exception occurred in {}, returncode={}'
                    .format(' '.join(cmd),
                            return_code))

    def run_image(self):
        cmd = [
            'podman', 'run',
            '-a=stdout',
            '--name=ansible-test'
        ]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
        )

        for line in proc.stdout:
            self.log.info(line.strip())

        return_code = proc.wait()
        if return_code != 0:
            self.log.error(
                'An exception occurred in {}, returncode={}'
                    .format(' '.join(cmd),
                            return_code))
