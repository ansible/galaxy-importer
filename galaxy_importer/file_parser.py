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
import json

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
            # TODO(awcrosby): consider check that ext_dir actually exists and fail import if not
            # TODO(awcrosby): consider check that ext_dir has exactly 3 dirs otherwise fail
            return [ext["args"]["ext_dir"] for ext in self.data["extensions"]]
        except KeyError:
            raise exc.FileParserError("'meta/extensions.yml is not in the expected format'")


class PatternsParser:
    """Load Ansible Patterns directories"""

    def __init__(self, collection_path, contents=None):
        self.collection_path = collection_path
        self.contents = contents or []
        self.relative_path = os.path.join("extensions", "patterns")
        self.path = os.path.join(self.collection_path, self.relative_path)
        self.dirs = []
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return
        self.dirs = os.listdir(self.path)

    def _load_meta_pattern(self, dir):
        """Loads meta/pattern.json for specified patterns directory"""
        pattern_path = self._get_meta_pattern_path(dir)

        try:
            with open(pattern_path) as fp:
                return json.load(fp)
        except Exception:
            rel_path = os.path.relpath(pattern_path, self.collection_path)
            raise exc.FileParserError(f"Error during parsing of {rel_path}")

    def _get_meta_pattern_path(self, dir):
        return os.path.join(
            self.path, dir, constants.META_PATTERN_DIR, constants.META_PATTERN_FILENAME
        )

    def validate_playbooks_count(self, dir, pattern_content):
        playbooks = list(
            filter(
                lambda content: content.content_type == constants.ContentType.PATTERNS
                and f"{constants.PATTERNS_NAME}.{dir}.playbooks." in content.name,
                self.contents,
            )
        )
        playbooks_count = len(playbooks)

        if playbooks_count > 1 and not self._has_primary_attr(pattern_content):
            raise exc.FileParserError("Multiple playbooks found, primary playbook must be defined")

    def _has_primary_attr(self, pattern_content):
        templates = pattern_content.get("aap_resources", {}).get("controller_job_templates", [])
        has_primary = any("primary" in t for t in templates)

        return has_primary

    def get_dirs(self):
        return self.dirs

    def get_meta_patterns(self):
        meta_patterns = []
        for dir in self.dirs:
            pattern_content = self._load_meta_pattern(dir)
            self.validate_playbooks_count(dir, pattern_content)
            meta_patterns.append(pattern_content)

        return meta_patterns
