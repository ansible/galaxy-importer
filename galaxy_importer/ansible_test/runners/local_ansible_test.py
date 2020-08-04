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


import os
import shutil
import subprocess

from galaxy_importer.ansible_test.runners.base import BaseTestRunner


class LocalAnsibleTestRunner(BaseTestRunner):
    """Run ansible-test locally with --docker or using venv."""
    def run(self):
        if not shutil.which('ansible'):
            self.log.error('ansible not found, skipping ansible-test')
            return

        version_proc = subprocess.Popen(
            ['ansible', '--version'],
            stdout=subprocess.PIPE,
            encoding='utf-8',
        )
        self.log.info(f'Using {list(version_proc.stdout)[0].rstrip()}')

        suffix = f'ansible_collections/{self.metadata.namespace}/{self.metadata.name}/'
        collection_dir = os.path.join(self.dir, suffix)

        cmd = [
            'ansible-test', 'sanity',
            '--docker',
            '--color', 'yes',
            '--failure-ok',
        ]

        collection_name = f'{self.metadata.namespace}-{self.metadata.name}-{self.metadata.version}'
        self.log.info(f'Running ansible-test sanity on {collection_name} ...')
        self.log.info(f'{" ".join(cmd)}')

        proc = subprocess.Popen(
            cmd,
            cwd=collection_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
        )

        for line in proc.stdout:
            self.log.info(line.strip())

        return_code = proc.wait()
        if return_code != 0:
            self.log.error('An exception occurred in {}, returncode={}, collection={}'.format(
                ' '.join(cmd), return_code, collection_name))
