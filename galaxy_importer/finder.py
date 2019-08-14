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

import collections
import itertools
import logging
import os

from galaxy_importer import constants
from galaxy_importer import exceptions as exc


default_logger = logging.getLogger(__name__)

Result = collections.namedtuple(
    'Result', ['content_type', 'path'])


class ContentFinder(object):
    """Searches for content in directories inside collection."""

    def find_contents(self, path, logger=None):
        """Finds contents in path and return the results.

        :rtype: Iterator[Result]
        :return: Iterator of find results.
        """

        self.path = path
        self.log = logger or default_logger

        self.log.info('Content search - Analyzing collection structure')
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
        for file_name in os.listdir(content_dir):
            file_path = os.path.join(content_dir, file_name)
            if os.path.isdir(file_path):
                raise exc.ContentFindError(
                    f'Directory detected: "{os.path.basename(file_path)}". '
                    'Nested plugins not supported.')
            if (not os.path.isfile(file_path)
                    or not file_name.endswith('.py')
                    or file_name == '__init__.py'):
                continue
            rel_path = os.path.relpath(file_path, self.path)
            yield Result(content_type, rel_path)

    def _find_roles(self, content_type, content_dir):
        for dir_name in os.listdir(content_dir):
            file_path = os.path.join(content_dir, dir_name)
            if not os.path.isdir(file_path):
                raise exc.ContentFindError(
                    'File inside "roles" directory not supported: '
                    f'"{os.path.basename(file_path)}".')
            rel_path = os.path.relpath(file_path, self.path)
            yield Result(content_type, rel_path)

    def _content_type_dirs(self):
        for content_type in constants.ContentType:
            if content_type == constants.ContentType.ROLE:
                yield content_type, 'roles', self._find_roles
            elif content_type == constants.ContentType.MODULE:
                yield content_type, 'plugins/modules', self._find_plugins
            else:
                yield (content_type, 'plugins/' + content_type.value,
                       self._find_plugins)
