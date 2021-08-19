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

import shutil
from subprocess import Popen, PIPE, STDOUT

from galaxy_importer import config
from galaxy_importer import exceptions
from galaxy_importer.ansible_test.builders.local_image_build import Build
from galaxy_importer.ansible_test.runners.base import BaseTestRunner


class LocalImageTestRunner(BaseTestRunner):
    """Run image locally with docker or podman."""

    def run(self):
        cfg = config.Config(config_data=config.ConfigFile.load())

        build = Build(
            self.filepath,
            f"{self.metadata.namespace}-{self.metadata.name}-{self.metadata.version}",
            cfg,
            self.log,
        )

        container_engine = build.get_container_engine(cfg)

        if not shutil.which(container_engine):
            self.log.warning(f'"{container_engine}" not found, skipping ansible-test sanity')
            return

        image_id = build.build_image()

        self.log.info("Running image...")
        self._run_image(image_id=image_id, container_engine=container_engine)

        build.cleanup()

    def _run_image(self, image_id, container_engine):
        cmd = [container_engine, "run", image_id, "LOCAL_IMAGE_RUNNER"]
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
