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

import abc
import logging
import os
from pathlib import Path
import re
import shutil
from subprocess import Popen, PIPE
import yaml

from galaxy_importer import constants
from galaxy_importer import exceptions as exc
from galaxy_importer import schema
from galaxy_importer.utils import markup as markup_utils

default_logger = logging.getLogger(__name__)


class ContentLoader(metaclass=abc.ABCMeta):
    def __init__(self, content_type, rel_path, root, doc_strings=None, cfg=None, logger=None):
        """
        :param content_type: Content type.
        :param rel_path: Path to content file or dir, relative to root path.
        :param root: Collection root path.
        :param doc_strings: ansible-doc output for all plugins in collection
        :param logger: Optional logger instance.

        ==Example==
        Given:
            root='/tmp/tmpgjbj53c9/ansible_collections/my_namespace/nginx'
            rel_path='modules/plugins/storage/another_subdir/s3.py'
        Names will be:
            fq_collection_name: my_namespace.nginx
            name: s3
            path_name: storage.another_subdir.s3
            fq_name: my_namespace.nginx.storage.another_subdir.s3
        """
        self.content_type = content_type
        self.rel_path = rel_path
        self.root = root

        self.name = self._make_name(self.rel_path)
        self._validate_name()
        self.path_name = self._make_path_name(self.rel_path, self.name)

        self.doc_strings = doc_strings or {}
        self.cfg = cfg
        self.log = logger or default_logger

    @abc.abstractmethod
    def load(self):
        """Loads data from content inside collection.
        :return: Content object."""

    @staticmethod
    @abc.abstractmethod
    def _make_name(rel_path):
        """Returns content name generated from it's path."""

    @staticmethod
    @abc.abstractmethod
    def _make_path_name(rel_path, name):
        """Returns subdirectories as part content name.
        'sub1.sub2.mod' for plugins/modules/sub1/sub2/mod.py"""

    @staticmethod
    def _get_fq_collection_name(root):
        root_parts = Path(root).parts
        return "{}.{}".format(*root_parts[-2:])

    def _get_fq_name(self, root, path_name):
        return "{}.{}".format(
            self._get_fq_collection_name(root),
            path_name,
        )

    def _validate_name(self):
        if not re.match(constants.CONTENT_NAME_REGEXP, self.name):
            raise exc.ContentNameError(
                f"{self.content_type.value} name invalid format: {self.name}"
            )

    def _log_loading(self):
        self.log.info(f"Loading {self.content_type.value} {self.path_name}")


class PluginLoader(ContentLoader):
    def load(self):
        self._log_loading()
        doc_strings = self._get_plugin_doc_strings()

        if self.cfg.run_flake8:
            for line in self._run_flake8(self.rel_path):
                self.log.warning(line)

        return schema.Content(
            name=self.path_name,
            content_type=self.content_type,
            doc_strings=doc_strings,
        )

    def _get_plugin_doc_strings(self):
        """Return plugin doc_strings, if exists, from collection doc_strings."""
        fq_name = self._get_fq_name(self.root, self.path_name)
        try:
            return self.doc_strings[self.content_type.value][fq_name]
        except KeyError:
            return None

    def _run_flake8(self, path):
        self.log.info(f"Linting {self.content_type.value} {self.path_name} via flake8...")

        if not shutil.which("flake8"):
            self.log.warning("flake8 not found, skipping")
            return

        cmd = [
            "flake8",
            "--exit-zero",
            "--isolated",
            "--extend-ignore",
            constants.FLAKE8_IGNORE_ERRORS,
            "--select",
            constants.FLAKE8_SELECT_ERRORS,
            "--max-line-length",
            str(constants.FLAKE8_MAX_LINE_LENGTH),
            "--",
            self.rel_path,
        ]

        self.log.debug("CMD: " + " ".join(cmd))
        proc = Popen(
            cmd,
            cwd=self.root,
            encoding="utf-8",
            stdout=PIPE,
        )

        for line in proc.stdout:
            yield line.strip()

    @staticmethod
    def _make_name(rel_path):
        return os.path.splitext(os.path.basename(rel_path))[0]

    @staticmethod
    def _make_path_name(rel_path, name):
        dirname_parts = Path(os.path.dirname(rel_path)).parts[2:]
        return ".".join(list(dirname_parts) + [name])


class RoleLoader(ContentLoader):
    def load(self):
        self._log_loading()
        description = self._get_metadata_description()
        readme = self._get_readme()

        if self.cfg.run_ansible_lint:
            self._lint_role(self.rel_path)

        return schema.Content(
            name=self.path_name,
            content_type=self.content_type,
            description=description,
            readme_file=readme.name,
            readme_html=markup_utils.get_html(readme),
        )

    @staticmethod
    def _make_name(rel_path):
        return os.path.basename(rel_path)

    @staticmethod
    def _make_path_name(rel_path, name):
        dirname_parts = Path(os.path.dirname(rel_path)).parts[1:]
        return ".".join(list(dirname_parts) + [name])

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
            "-p",
            "-x",
            "metadata",
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


def get_loader_cls(content_type):
    if content_type.category == constants.ContentCategory.ROLE:
        return RoleLoader
    elif content_type.category in [
        constants.ContentCategory.PLUGIN,
        constants.ContentCategory.MODULE,
    ]:
        return PluginLoader
    return None
