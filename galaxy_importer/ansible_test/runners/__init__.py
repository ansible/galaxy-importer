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

from .local_ansible_test import LocalAnsibleTestRunner
from .local_image import LocalImageTestRunner
from .openshift_job import OpenshiftJobTestRunner


default_logger = logging.getLogger(__name__)


def get_runner(cfg):
    """Decide which runner class to run ansible-test based on config."""

    if not cfg.run_ansible_test:
        return None

    if cfg.infra_osd:
        return OpenshiftJobTestRunner

    if cfg.ansible_test_local_image:
        return LocalImageTestRunner

    return LocalAnsibleTestRunner
