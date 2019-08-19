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
import re

from galaxy_importer import constants
from galaxy_importer import exceptions as exc
from galaxy_importer import schema


default_logger = logging.getLogger(__name__)

ANSIBLE_DOC_SUPPORTED_TYPES = [
    'become', 'cache', 'callback', 'cliconf', 'connection',
    'httpapi', 'inventory', 'lookup', 'shell', 'module', 'strategy', 'vars']


class ContentLoader(metaclass=abc.ABCMeta):

    def __init__(self, content_type, rel_path, root, logger=None):
        """
        :param content_type: Content type.
        :param rel_path: Path to content file or dir, relative to root path.
        :param root: Collection root path.
        :param logger: Optional logger instance.
        """
        self.content_type = content_type
        self.rel_path = rel_path
        self.root = root
        self.name = self._make_name()

        self.doc_strings = None
        self.description = None
        self.readme_file = None
        self.readme_html = None

        self.log = logger or default_logger
        self._validate_name()

    @abc.abstractmethod
    def load(self):
        """Loads data from content inside collection.
        :return: Content object."""
        pass

    @abc.abstractmethod
    def _make_name(self):
        """Returns content name generated from it's path."""
        pass

    def _validate_name(self):
        if not re.match(constants.NAME_REGEXP, self.name):
            raise exc.ContentNameError(
                f'{self.content_type.value} name invalid format: {self.name}')

    def _log_loading(self):
        self.log.info(' ')
        self.log.info(
            f'===== LOADING {self.content_type.name}: {self.name} =====')


class PluginLoader(ContentLoader):
    def load(self):
        self._log_loading()
        if self.content_type.value in ANSIBLE_DOC_SUPPORTED_TYPES:
            self._get_doc_strings()

        return schema.Content(
            name=self.name,
            content_type=self.content_type,
            doc_strings=self.doc_strings,
        )

    def _make_name(self):
        return os.path.splitext(os.path.basename(self.rel_path))[0]

    def _get_doc_strings(self):
        self.log.info('Getting doc strings via ansible-doc')
        pass


class RoleLoader(ContentLoader):
    def load(self):
        self._log_loading()
        self._lint()
        self._get_readme()
        self._get_metadata_description()

        return schema.Content(
            name=self.name,
            content_type=self.content_type,
            description=self.description,
            readme_file=self.readme_file,
            readme_html=self.readme_html,
        )

    def _make_name(self):
        return os.path.basename(self.rel_path)

    def _lint(self):
        self.log.info('Linting role via ansible-lint')
        pass

    def _get_readme(self):
        self.log.info('Getting role readme')
        pass

    def _get_metadata_description(self):
        self.log.info('Getting role description')
        pass


def get_loader_cls(content_type):
    if content_type == constants.ContentType.ROLE:
        loader_cls = RoleLoader
    else:
        loader_cls = PluginLoader
    return loader_cls
