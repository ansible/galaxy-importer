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

from galaxy_importer import config
import logging


default_logger = logging.getLogger(__name__)


class AnsibleTestRunner(object):
    """Runs ansible-test on collection, dependent on config."""

    def __init__(self, logger=None):
        self.log = logger or default_logger
        self.cfg = config.Config()

    def run(self):
        if not self.cfg.run_ansible_test:
            return

        if not self.cfg.infra_pulp:
            self._run_ansible_test_local()
            return

        image = self._build_img_with_artifact()

        if self.cfg.infra_osd:
            self._run_image_openshift_job(image)
        else:
            self._run_image_local(image)

    def _run_ansible_test_local(self):
        """Run ansible-test locally with --docker or using venv."""

    def _build_img_with_artifact(self):
        """Use pulp-container to build ansible-test image with artifact inside."""
        return ''

    def _run_image_local(self, image):
        """Run image locally with docker or podman."""

    def _run_image_openshift_job(self, image):
        """Run image as an openshift job."""
