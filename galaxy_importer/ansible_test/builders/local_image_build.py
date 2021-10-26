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
import shutil
import tempfile

from galaxy_importer import exceptions
from shutil import copy
from subprocess import Popen, PIPE, STDOUT, run, CalledProcessError

default_logger = logging.getLogger(__name__)


class Build(object):
    """Use docker/podman to build ansible-test image with artifact inside."""

    def __init__(self, filepath, collection_name, cfg, logger=default_logger):
        self.cfg = cfg
        self.container_engine = Build.get_container_engine(cfg)
        self.filepath = filepath
        self.log = logger or default_logger
        self.image = ""
        self.working_dir = tempfile.TemporaryDirectory()

    def build_image(self):
        if self.container_engine == "docker":
            self.log.info("Building Dockerfile")
        else:
            self.log.info("Building ContainerFile")
        Build._build_dockerfile(self.working_dir.name)
        Build._copy_collection_file(dir=self.working_dir.name, filepath=self.filepath)

        self.log.info("Building image...")
        self.image = Build._build_image_with_artifact(
            container_engine=self.container_engine, dir=self.working_dir.name
        )
        return self.image

    def cleanup(self):
        self.log.info("Removing temporary files, image and container")
        self.working_dir.cleanup()

        cmd = [self.container_engine, "image", "rm", "-f", self.image]
        try:
            run(cmd)
        except CalledProcessError as e:
            raise exceptions.AnsibleTestError(
                "An exception occurred in: {}, message={}".format(" ".join(cmd), e.msg)
            )

    @staticmethod
    def get_container_engine(cfg):
        if cfg.local_image_docker is True:
            return "docker"
        else:
            return "podman"

    def _build_dockerfile(dir):
        pkg_dockerfile = pkg_resources.resource_filename(
            "galaxy_importer", "ansible_test/container/Dockerfile"
        )
        file_location = os.path.join(dir, "Dockerfile")
        shutil.copyfile(pkg_dockerfile, file_location)

        with open(file_location, "r+") as f:
            lines = f.readlines()
            for index, line in enumerate(lines):
                if "ENV HOME" in line:
                    # TODO move RUN command to base image
                    lines.insert(index - 1, "\nRUN chown -R user1:root /archive\n")
                    lines.insert(index - 1, "\nCOPY archive.tar.gz /archive/archive.tar.gz\n")
                    break
            f.seek(0)
            f.writelines(lines)

    def _build_image_with_artifact(container_engine, dir):
        pkg_entrypoint = pkg_resources.resource_filename(
            "galaxy_importer", "ansible_test/container/entrypoint.sh"
        )
        shutil.copyfile(pkg_entrypoint, os.path.join(dir, "entrypoint.sh"))

        cmd = [container_engine, "build", ".", "--quiet"]
        proc = Popen(
            cmd,
            cwd=dir,
            stdout=PIPE,
            stderr=STDOUT,
            encoding="utf-8",
        )

        image_id = ""
        for line in proc.stdout:
            image_id = line.strip()

        return_code = proc.wait()
        if return_code != 0:
            raise exceptions.AnsibleTestError(
                "An exception occurred in {}, returncode={}".format(" ".join(cmd), return_code)
            )
        if container_engine == "docker":
            image_id = image_id.split(":")[-1]
        return image_id

    def _copy_collection_file(dir, filepath):
        path = os.path.join(dir, "archive.tar.gz")
        copy(filepath, path)
