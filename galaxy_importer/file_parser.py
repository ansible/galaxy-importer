# (c) 2012-2023, Ansible by Red Hat
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
import yaml

from galaxy_importer import constants
from galaxy_importer import exceptions as exc
from galaxy_importer.utils import requires_ansible_version

default_logger = logging.getLogger(__name__)


class RuntimeFileParser:
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
                raise exc.FileParserError("Error during parsing of runtime.yml")

    def get_requires_ansible(self):
        if not self.data:
            raise exc.FileParserError(
                "'requires_ansible' in meta/runtime.yml is mandatory, "
                "but no meta/runtime.yml found"
            )
        requires_ansible = self.data.get("requires_ansible")
        if not requires_ansible:
            raise exc.FileParserError(
                "'requires_ansible' in meta/runtime.yml is mandatory, "
                "but 'requires_ansible' not found"
            )
        if len(requires_ansible) > constants.MAX_LENGTH_REQUIRES_ANSIBLE:
            raise exc.FileParserError(
                f"'requires_ansible' must not be greater than "
                f"{constants.MAX_LENGTH_REQUIRES_ANSIBLE} characters"
            )
        try:
            requires_ansible_version.validate(requires_ansible)
            return requires_ansible
        except ValueError:
            raise exc.FileParserError("'requires_ansible' is not a valid requirement specification")


class ExtensionsFileParser:
    """Load meta/extensions.yml."""

    def __init__(self, collection_path):
        self.path = os.path.join(collection_path, "meta/extensions.yml")
        self.data = None
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path) as fp:
            try:
                self.data = yaml.safe_load(fp)
            except Exception:
                raise exc.FileParserError("Error during parsing of extensions.yml")

    def get_extension_dirs(self):
        try:
            if not self.data:
                return []
            # TODO: consider check that ext_dir actually exists and fail import if not
            # TODO: consider check that ext_dir has exactly 3 dirs otherwise fail
            return [ext["args"]["ext_dir"] for ext in self.data["extensions"]]
        except KeyError:
            raise exc.FileParserError("'meta/extensions.yml is not in the expected format'")
