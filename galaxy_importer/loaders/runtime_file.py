# (c) 2012-2019, Ansible by Red Hat
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
import semantic_version
import yaml

from galaxy_importer import constants
from galaxy_importer import exceptions as exc

default_logger = logging.getLogger(__name__)


class RuntimeFileLoader:
    """Load meta/runtime.yml."""

    def __init__(self, collection_path):
        self.path = os.path.join(collection_path, "meta/runtime.yml")
        self.data = None
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path) as fp:
            try:
                self.data = yaml.safe_load(fp)
            except Exception:
                raise exc.RuntimeFileError("Error during parsing of runtime.yml")

    def get_requires_ansible(self):
        if not self.data:
            raise exc.RuntimeFileError(
                "'requires_ansible' in meta/runtime.yml is mandatory, "
                "but no meta/runtime.yml found"
            )
        requires_ansible = self.data.get("requires_ansible")
        if not requires_ansible:
            raise exc.RuntimeFileError(
                "'requires_ansible' in meta/runtime.yml is mandatory, "
                "but 'requires_ansible' not found"
            )
        if len(requires_ansible) > constants.MAX_LENGTH_REQUIRES_ANSIBLE:
            raise exc.RuntimeFileError(
                f"'requires_ansible' must not be greater than "
                f"{constants.MAX_LENGTH_REQUIRES_ANSIBLE} characters"
            )
        try:
            semantic_version.SimpleSpec(requires_ansible)
            return requires_ansible
        except ValueError:
            raise exc.RuntimeFileError(
                "'requires_ansible' is not a valid semantic_version requirement specification"
            )
