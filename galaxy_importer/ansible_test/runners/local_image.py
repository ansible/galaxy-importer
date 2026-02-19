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
from subprocess import PIPE, STDOUT, Popen

from galaxy_importer import config, exceptions
from galaxy_importer.ansible_test.runners.base import BaseTestRunner


class LocalImageTestRunner(BaseTestRunner):
    """
    Run `ansible-test sanity` in container defined in repo and hosted on quay.

    Container defined at galaxy_importer/ansible_test/container

    Image used is hosted on quay: quay.io/cloudservices/automation-hub-ansible-test
    """

    def run(self):
        cfg = config.Config(config_data=config.ConfigFile.load())

        # Get preferred container image and check if installed
        container_engine = "podman"
        if cfg.local_image_docker is True:
            container_engine = "docker"
        if not shutil.which(container_engine):
            self.log.warning(f'"{container_engine}" not found, skipping ansible-test sanity')
            return

        # Copy user-provided archive into path that can be used as volume
        archive_path = os.path.join(self.dir, "archive.tar.gz")
        self.log.debug(f"archive_path={archive_path}")
        shutil.copy(self.filepath, archive_path)
        volume = f"{archive_path}:/archive/archive.tar.gz"

        self.log.info("Pulling image...")
        self._pull_image(container_engine=container_engine)

        self.log.info("Running image...")
        self._run_image(container_engine=container_engine, volume=volume)

    def _pull_image(self, container_engine):
        # TODO: use a separate image repo, repo or org is private
        cmd = [
            container_engine,
            "pull",
            "quay.io/cloudservices/automation-hub-ansible-test",
        ]
        self.log.debug(f"cmd={cmd}")

        proc = Popen(
            cmd,
            stdout=PIPE,
            stderr=STDOUT,
            encoding="utf-8",
        )

        for line in proc.stdout:
            self.log.info(line.strip())

        return_code = proc.wait()
        if return_code != 0:
            raise exceptions.AnsibleTestError(
                "An exception occurred in {}, returncode={}".format(" ".join(cmd), return_code)
            )

    def _run_image(self, container_engine, volume):
        cmd = [
            container_engine, "run",
            "-v", volume,
            "quay.io/cloudservices/automation-hub-ansible-test",
            "LOCAL_IMAGE_RUNNER",
        ]  # fmt: skip
        self.log.debug(f"cmd={cmd}")

        proc = Popen(
            cmd,
            stdout=PIPE,
            stderr=STDOUT,
            encoding="utf-8",
        )

        for line in proc.stdout:
            self.log.info(line.strip())

        return_code = proc.wait()
        if return_code != 0:
            raise exceptions.AnsibleTestError(
                "An exception occurred in {}, returncode={}".format(" ".join(cmd), return_code)
            )
