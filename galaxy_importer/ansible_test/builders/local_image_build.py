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
import requests
import tempfile

from galaxy_importer import config
from galaxy_importer import exceptions
from shutil import copy
from subprocess import Popen, PIPE, STDOUT, run, CalledProcessError

config_data = config.ConfigFile.load()
cfg = config.Config(config_data=config_data)
default_logger = logging.getLogger(__name__)


class Build(object):
    """Use docker/podman to build ansible-test image with artifact inside."""
    def __init__(self, filepath, collection_name, logger=default_logger):
        self.filepath = filepath
        self.log = logger or default_logger
        self.image = ''
        self.working_dir = tempfile.TemporaryDirectory()

    def build_image(self):
        self.log.info('Building Dockerfile')
        Build._build_dockerfile(self.working_dir.name)
        Build._copy_collection_file(
            dir=self.working_dir.name,
            filepath=self.filepath
        )

        self.log.info('Building image...')
        self.image = Build._build_image_with_artifact(dir=self.working_dir.name)
        return self.image

    def cleanup(self):
        self.log.info('Removing temporary files, image and container')
        self.working_dir.cleanup()

        cmd = ['docker', 'image', 'rm', '-f', self.image]
        try:
            run(cmd)
        except CalledProcessError as e:
            raise exceptions.AnsibleTestError(
                'An exception occurred in: {}, message={}'.format(' '.join(cmd), e.msg))

    def _build_dockerfile(dir):
        url = 'https://raw.githubusercontent.com/ansible/galaxy-importer \
            /master/docker/ansible-test/Dockerfile'
        file_location = os.path.join(dir, 'Dockerfile')
        with requests.get(url, allow_redirects=True) as r:
            with open(file_location, 'wb') as f:
                f.write(r.content)
        with open(file_location, 'r+') as f:
            lines = f.readlines()
            for index, line in enumerate(lines):
                if 'ENV HOME' in line:
                    # TODO move RUN command to base image
                    lines.insert(index - 1, '\nRUN chown -R user1:root /archive\n')
                    lines.insert(index - 1, '\nCOPY archive.tar.gz /archive/archive.tar.gz\n')
                    break
            f.seek(0)
            f.writelines(lines)

    def _build_image_with_artifact(dir):
        cmd = ['docker', 'build', '.', '--quiet']
        proc = Popen(
            cmd,
            cwd=dir,
            stdout=PIPE,
            stderr=STDOUT,
            encoding='utf-8',
        )

        result = ''
        for line in proc.stdout:
            result = line.strip()

        return_code = proc.wait()
        if return_code != 0:
            raise exceptions.AnsibleTestError(
                'An exception occurred in {}, returncode={}'
                .format(' '.join(cmd), return_code))
        return result.split(':')[-1]

    def _copy_collection_file(dir, filepath):
        path = os.path.join(dir, 'archive.tar.gz')
        copy(filepath, path)
