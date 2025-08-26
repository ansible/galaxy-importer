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

import itertools
import logging
import os
from typing import NamedTuple

import attr

from galaxy_importer import constants
from galaxy_importer.file_parser import ExtensionsFileParser, PatternsParser
from galaxy_importer.exceptions import ContentFindError

default_logger = logging.getLogger(__name__)


class Result(NamedTuple):
    content_type: constants.ContentType
    path: str


class PatternsFindError(ContentFindError):
    def __init__(self, message="Default overwrite error occurred"):
        self.message = message
        super().__init__(self.message)


ROLE_SUBDIRS = ["tasks", "vars", "handlers", "meta"]


@attr.s(slots=True)
class PatternsFinder:
    path = attr.ib()
    log = attr.ib()

    def set_result(self, content_dir, content_type, file):
        file_path = os.path.join(content_dir, file)
        rel_path = self.get_rel_path(file_path)
        yield Result(content_type, rel_path)

    def set_results(self, content_dir, content_type, files):
        for file in files:
            yield from self.set_result(content_dir, content_type, file)

    def get_rel_path(self, content_dir):
        return os.path.relpath(content_dir, self.path)

    def find_readme(self, content_dir):
        readme = self._find_file(content_dir, "readme", [".md"])
        yield from self.set_result(content_dir, constants.ContentType.PATTERNS, readme)

    def find_meta_pattern(self, content_dir):
        pattern = self._find_file(
            os.path.join(content_dir, constants.META_PATTERN_DIR),
            "pattern",
            allowed_extensions=[".json"],
        )
        yield from self.set_result(
            content_dir,
            constants.ContentType.PATTERNS,
            os.path.join(constants.META_PATTERN_DIR, pattern),
        )

    def find_playbooks(self, content_dir):
        playbooks_dir = os.path.join(content_dir, "playbooks")

        if not os.path.exists(playbooks_dir):
            rel_path = self.get_rel_path(content_dir)
            raise ContentFindError(f"{rel_path} must contain playbooks directory")

        playbooks = self._map_dir(playbooks_dir)
        if len(playbooks) < 1:
            rel_path = self.get_rel_path(playbooks_dir)
            raise ContentFindError(f"{rel_path} must containt atleast one playbook")

        yield from self.set_results(playbooks_dir, constants.ContentType.PATTERNS, playbooks)

    def find_templates(self, content_dir):
        templates_dir = os.path.join(content_dir, "templates")
        if not os.path.exists(templates_dir):
            rel_path = self.get_rel_path(templates_dir)
            self.log.info(f"{rel_path} not found, skipping")
        else:
            templates = self._map_dir(templates_dir)
            yield from self.set_results(templates_dir, constants.ContentType.PATTERNS, templates)

    def _find_file(
        self, content_dir, expected_filename, allowed_extensions=(".yml", ".yaml"), required=True
    ):
        rel_path = self.get_rel_path(os.path.join(content_dir, expected_filename))

        req_file_exc_msg = f"{rel_path}({'/'.join(allowed_extensions)}) not found"

        if not os.path.exists(content_dir) and required:
            raise ContentFindError(req_file_exc_msg)
        else:
            for content in os.listdir(content_dir):
                if os.path.isfile(os.path.join(content_dir, content)):
                    file, extension = os.path.splitext(content)
                    if (
                        extension
                        and extension.lower() in allowed_extensions
                        and expected_filename == file.lower()
                    ):
                        return content

        if required:
            raise ContentFindError(req_file_exc_msg)

    def _map_dir(self, content_dir):
        dirs = []
        for dirpath, _, filenames in os.walk(content_dir):
            for filename in filenames:
                dirs.append(os.path.join(dirpath, filename))

        return dirs

    def find_content(self, content_type, content_dir):
        # readme.md
        yield from self.find_readme(content_dir)

        # meta/pattern.json
        yield from self.find_meta_pattern(content_dir)

        # playbooks/
        yield from self.find_playbooks(content_dir)

        # templates/
        yield from self.find_templates(content_dir)


class ContentFinder:
    """Searches for content in directories inside collection."""

    def find_contents(self, path, logger=None):
        """Finds contents in path and return the results.

        :rtype: Iterator[Result]
        :return: Iterator of find results.
        """

        self.path = path
        self.log = logger or default_logger

        self.log.info("Finding content inside collection")

        contents = self._find_content()

        try:
            first = next(contents)
        except StopIteration:
            return []
        else:
            return itertools.chain([first], contents)

    def _find_content(self):
        for content_type, directory, func in self._content_type_dirs():
            content_path = os.path.join(self.path, directory)
            if not os.path.exists(content_path):
                continue
            yield from func(content_type, content_path)

    def _find_plugins(self, content_type, content_dir):
        """Find all python files anywhere inside content_dir."""
        for path, _, files in os.walk(content_dir):
            for file in files:
                if not file.endswith((".py", ".ps1")) or file == "__init__.py":
                    continue
                file_path = os.path.join(path, file)
                rel_path = os.path.relpath(file_path, self.path)
                yield Result(content_type, rel_path)

    def _find_playbooks(self, content_type, content_dir):
        for root, _, filenames in os.walk(content_dir):
            if root != content_dir:
                continue
            for filename in filenames:
                _, extension = os.path.splitext(filename)
                if extension and extension.lower() in [".yml", ".yaml"]:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, self.path)
                    yield Result(content_type, rel_path)

    def _find_roles(self, content_type, content_dir):
        """Find all dirs inside roles dir where contents match a role."""

        def is_dir_a_role(current_dir):
            """Check for contents indicating directory is a role."""
            _, dirs, _ = next(os.walk(current_dir))
            return bool(set(ROLE_SUBDIRS) & set(dirs))

        def recurse_role_dir(path):
            """Iterate over all subdirs and yield roles."""
            if is_dir_a_role(path):
                rel_path = os.path.relpath(path, self.path)
                yield Result(content_type, rel_path)
                return
            path, dirs, _ = next(os.walk(path))
            for dir in dirs:
                yield from recurse_role_dir(os.path.join(path, dir))

        yield from recurse_role_dir(content_dir)

    def _content_type_dirs(self):
        for content_type in constants.ContentType:
            if content_type == constants.ContentType.PLAYBOOK:
                yield content_type, "playbooks", self._find_playbooks
            elif content_type == constants.ContentType.ROLE:
                yield content_type, "roles", self._find_roles
            elif content_type == constants.ContentType.MODULE:
                yield content_type, "plugins/modules", self._find_plugins
            else:
                yield (
                    content_type,
                    "plugins/" + content_type.value,
                    self._find_plugins,
                )

        for content_type, full_path in self._get_ext_types_and_path():
            yield content_type, full_path, self._find_plugins

        patterns_finder = PatternsFinder(self.path, self.log)
        for content_type, full_path in self._get_patterns_path():
            yield content_type, full_path, patterns_finder.find_content

    def _get_ext_types_and_path(self):
        extension_dirs = ExtensionsFileParser(self.path).get_extension_dirs()

        if not extension_dirs:
            return []

        # remove ext_dir not currently allowed in the content list
        for ext_dir in list(extension_dirs):
            if ext_dir not in constants.ALLOWED_EXTENSION_DIRS:
                self.log.warning(
                    f"The extension type '{ext_dir}' listed in 'meta/extensions.yml' is "
                    "custom and will not be listed in Galaxy's contents nor documentation"
                )
                extension_dirs.remove(ext_dir)

        content_types_and_dirs = [
            (constants.ContentType(dir), f"extensions/{dir}") for dir in extension_dirs
        ]

        return content_types_and_dirs

    def _get_patterns_path(self):
        patterns_parser = PatternsParser(self.path)
        patterns_dirs = patterns_parser.get_dirs()

        if not patterns_dirs:
            return []

        content_types_and_dirs = [
            (constants.ContentType.PATTERNS, os.path.join(patterns_parser.relative_path, dir))
            for dir in patterns_dirs
        ]

        return content_types_and_dirs


@attr.s
class FileWalker:
    collection_path = attr.ib()
    file_errors = attr.ib(factory=list)

    def walk(self):
        full_collection_path = os.path.abspath(self.collection_path)

        for dirpath, dirnames, filenames in os.walk(
            full_collection_path, onerror=self.on_walk_error, followlinks=False
        ):
            for dirname in dirnames:
                dir_full_path = os.path.join(dirpath, dirname)
                yield dir_full_path

            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                yield full_path

    def on_walk_error(self, walk_error):
        default_logger.warning("walk error on %s: %s", walk_error.filename, walk_error)
        self.file_errors.append(walk_error)
