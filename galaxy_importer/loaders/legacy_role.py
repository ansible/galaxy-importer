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
import shutil
from subprocess import Popen, PIPE
import yaml

from galaxy_importer import constants
from galaxy_importer import exceptions as exc
from galaxy_importer.utils import markup as markup_utils
from galaxy_importer.loaders.content import ContentLoader

default_logger = logging.getLogger(__name__)


ROLE_META_FILES = ["meta/main.yml", "meta/main.yaml", "meta.yml", "meta.yaml"]


class LegacyRoleLoader(ContentLoader):
    _metadata_path = None
    _metadata = None

    def load(self):
        self._log_loading()
        description = self._get_metadata_description()
        readme = self._get_readme()

        if self.cfg.run_ansible_lint:
            self._lint_role(self.rel_path)

        if self._metadata_path is None:
            self._metadata_path = self._find_metadata_file_path(self.root, self.rel_path)

        self._metadata = self._get_metadata()
        galaxy_info = self._metadata.get("galaxy_info", {})
        min_ansible_version = galaxy_info.get("min_ansible_version")
        license = galaxy_info.get("license", None)
        tags = galaxy_info.get("tags", [])
        dependencies = galaxy_info.get("dependencies", [])

        return dict(
            name=self.path_name,
            content_type=self.content_type.name,
            description=description,
            readme_file=readme.name,
            readme_html=markup_utils.get_html(readme),
            tags=tags,
            min_ansible_version=min_ansible_version,
            license=license,
            dependencies=dependencies,
        )

    @staticmethod
    def _make_name(rel_path):
        return os.path.basename(rel_path)

    @staticmethod
    def _make_path_name(rel_path, name):
        # dirname_parts = Path(os.path.dirname(rel_path)).parts[1:]
        # return ".".join(list(dirname_parts) + [name])
        return os.path.basename(os.path.dirname(rel_path)) + "." + name

    def _lint_role(self, path):
        """Log ansible-lint output.

        ansible-lint stdout are linter violations, they are logged as warnings.

        ansible-lint stderr includes info about vars, file discovery,
        summary of linter violations, config suggestions, and raised errors.
        Only raised errors are logged, they are logged as errors.
        """

        self.log.info(f"Linting role {self.path_name} via ansible-lint...")

        if not shutil.which("ansible-lint"):
            self.log.warning("ansible-lint not found, skipping lint of role")
            return

        cmd = [
            "/usr/bin/env",
            f"ANSIBLE_LOCAL_TEMP={self.cfg.ansible_local_tmp}",
            "ansible-lint",
            path,
            "--parseable",
            "--skip-list",
            "metadata",
            "--project-dir",
            os.path.dirname(path),
        ]
        self.log.debug("CMD: " + " ".join(cmd))
        proc = Popen(
            cmd,
            cwd=self.root,
            encoding="utf-8",
            stdout=PIPE,
            stderr=PIPE,
        )
        proc.wait()

        for line in proc.stdout:
            self.log.warning(line.strip())

        for line in proc.stderr:
            if line.startswith(constants.ANSIBLE_LINT_ERROR_PREFIXES):
                self.log.error(line.rstrip())

    def _get_readme(self):
        readme = markup_utils.get_readme_doc_file(os.path.join(self.root, self.rel_path))
        if not readme:
            raise exc.ContentLoadError("No role readme found.")
        return readme

    def _get_metadata(self):
        meta_path = self._find_metadata_file_path(self.root, self.rel_path)

        if not self._metadata_path:
            self.log.warning("Could not get role description, no role metadata found")
            return {}

        with open(meta_path) as fp:
            try:
                role_metadata = yaml.safe_load(fp)
            except Exception:
                self.log.error("Error during parsing of role metadata")
                return {}

        return role_metadata

    def _get_metadata_description(self):
        description = None
        meta_path = self._find_metadata_file_path(self.root, self.rel_path)

        if not meta_path:
            self.log.warning("Could not get role description, no role metadata found")
            return description

        with open(meta_path) as fp:
            try:
                role_metadata = yaml.safe_load(fp)
            except Exception:
                self.log.error("Error during parsing of role metadata")

        try:
            description = role_metadata["galaxy_info"]["description"]
        except KeyError:
            self.log.warning("No role description found in role metadata")
        return description

    @staticmethod
    def _find_metadata_file_path(root, rel_path):
        """Gets path to role metadata file."""
        for file in constants.ROLE_META_FILES:
            meta_path = os.path.join(root, rel_path, file)
            if os.path.exists(meta_path):
                return meta_path
        return None
