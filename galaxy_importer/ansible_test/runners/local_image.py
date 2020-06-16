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

from galaxy_importer import exceptions
from galaxy_importer.ansible_test.runners.base import BaseTestRunner
from galaxy_importer.ansible_test.builders.pulp_build import Build
from galaxy_importer.ansible_test.builders.pulp_server import PulpServer

default_logger = logging.getLogger(__name__)


class LocalImageTestRunner(BaseTestRunner):
    """Run image locally with docker or podman."""
    def run(self):
        pulp = PulpServer(logger=self.log)
        pulp.start()

        pulp_container_build = Build(
            api_url=pulp.get_api_url(),
            pulp_artifact_file=self.file,
            metadata=self.metadata,
            logger=self.log,
        )

        # Build OCI ansible-test image and retrieve link to it
        pulp_container_build.build()

        registry_path = pulp_container_build.get_registry_href()

        # Run ansible-test image via Podman and capture output
        self._pull_image(registry_path)
        self._run_image(registry_path)

        self._image_cleanup(registry_path)
        pulp_container_build.cleanup()
        pulp.cleanup()

    def _pull_image(self, registry_path):
        cmd = ['podman', 'pull', '--tls-verify=false', registry_path]
        try:
            subprocess.run(cmd)
        except subprocess.CalledProcessError as e:
            raise exceptions.AnsibleTestError(
                'An exception occurred in: {}, message={}'.format(' '.join(cmd), e.msg))

    def _run_image(self, registry_path):
        cmd = ['podman', 'run', registry_path]
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
            raise exceptions.AnsibleTestError(
                'An exception occurred in {}, returncode={}'
                .format(' '.join(cmd), return_code))

    def _image_cleanup(self, registry_path):
        cmd = ['podman', 'image', 'rm', registry_path]
        subprocess.run(cmd, encoding='utf-8')
