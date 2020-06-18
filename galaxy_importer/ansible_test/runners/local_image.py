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

from galaxy_importer import exceptions
from galaxy_importer.ansible_test.builders.local_image_build import Build
from galaxy_importer.ansible_test.runners.base import BaseTestRunner
from subprocess import Popen, PIPE, STDOUT


class LocalImageTestRunner(BaseTestRunner):
    """Run image locally with docker or podman."""
    def run(self):
        build = Build(
            self.filepath,
            f'{self.metadata.namespace}-{self.metadata.name}-{self.metadata.version}',
            self.log)

        image_id = build.build_image()

        self.log.info('Running image...')
        self._run_image(image_id=image_id)

        build.cleanup()

    def _run_image(self, image_id):
        cmd = ['docker', 'run', image_id]
        proc = Popen(
            cmd,
            stdout=PIPE,
            stderr=STDOUT,
            encoding='utf-8',
        )

        for line in proc.stdout:
            self.log.info(line.strip())

        return_code = proc.wait()
        if return_code != 0:
            raise exceptions.AnsibleTestError(
                'An exception occurred in {}, returncode={}'
                .format(' '.join(cmd), return_code))
