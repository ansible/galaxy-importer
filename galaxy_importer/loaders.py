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
from copy import deepcopy
import json
import logging
import os
from pathlib import Path
import re
from subprocess import Popen, PIPE

from galaxy_importer import constants
from galaxy_importer import exceptions as exc
from galaxy_importer import schema
from galaxy_importer.utils import markup as markup_utils


default_logger = logging.getLogger(__name__)

ANSIBLE_DOC_SUPPORTED_TYPES = [
    'become', 'cache', 'callback', 'cliconf', 'connection',
    'httpapi', 'inventory', 'lookup', 'shell', 'module', 'strategy', 'vars']
ANSIBLE_DOC_KEYS = ['doc', 'metadata', 'examples', 'return']
ANSIBLE_LINT_EXCEPTION_RETURN_CODE = 1


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
        if not re.match(constants.CONTENT_NAME_REGEXP, self.name):
            raise exc.ContentNameError(
                f'{self.content_type.value} name invalid format: {self.name}')

    def _log_loading(self):
        self.log.info(' ')
        self.log.info(
            f'===== LOADING {self.content_type.name}: {self.name} =====')


class PluginLoader(ContentLoader):
    def load(self):
        self._log_loading()
        self.doc_strings = self._get_doc_strings()

        return schema.Content(
            name=self.name,
            content_type=self.content_type,
            doc_strings=self.doc_strings,
        )

    def _make_name(self):
        return os.path.splitext(os.path.basename(self.rel_path))[0]

    def _get_doc_strings(self):
        if self.content_type.value not in ANSIBLE_DOC_SUPPORTED_TYPES:
            return None

        self.log.info('Getting doc strings via ansible-doc')
        json_output = self._run_ansible_doc()

        if not json_output:
            return
        data = json.loads(json_output)
        if self.name not in data.keys():
            self.log.error(f'No "{self.name}" key in ansible-doc output')
            return None

        data = self._transform_params(data)
        return {
            key: data[self.name].get(key, None)
            for key in ANSIBLE_DOC_KEYS
        }

    def _transform_params(self, data):
        def transform(dict_of_dict):
            return [
                {'name': key, **deepcopy(dict_of_dict[key])} for
                key in dict_of_dict.keys()
            ]

        doc = data[self.name]['doc']
        if doc and 'options' in doc.keys() and \
                isinstance(doc['options'], dict):
            doc['options'] = transform(doc['options'])

        ret = data[self.name]['return']
        if ret and isinstance(ret, dict):
            data[self.name]['return'] = transform(ret)

        return data

    def _run_ansible_doc(self):
        cmd = [
            'ansible-doc',
            '--type', self.content_type.value,
            '-M', os.path.dirname(self.rel_path),
            self.name,
            '--json']
        self.log.debug('CMD: {}'.format(' '.join(cmd)))
        proc = Popen(cmd, cwd=self.root, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode:
            self.log.error(f'Error running ansible-doc: {stderr}')
            return None
        return stdout


class RoleLoader(ContentLoader):
    def load(self):
        self._log_loading()
        for line in self._lint_role(self.rel_path):
            self.log.warning(line)
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

    def _lint_role(self, path):
        self.log.info('Linting role via ansible-lint')
        cmd = [
            'ansible-lint', path,
            '-p',
            '-x', 'metadata',
        ]
        self.log.debug('CMD: ' + ' '.join(cmd))
        proc = Popen(
            cmd,
            cwd=self.root,
            encoding='utf-8',
            stdout=PIPE,
        )

        for line in proc.stdout:
            # shorten linter message filepath to last 3 parts of path
            # /tmp/tmp_zyx/roles/role_test1/tasks/main.yml:19: [E201] Trail...
            line_list = line.split(' ')
            rel_path = os.path.join(*Path(line_list[0]).parts[-3:])
            line_list[0] = rel_path
            line = ' '.join(line_list)
            yield line.strip()

        # returncode 1 is app exception, 0 is no linter err, 2 is linter err
        if proc.wait() == ANSIBLE_LINT_EXCEPTION_RETURN_CODE:
            yield 'Exception running ansible-lint, could not complete linting'

    def _get_readme(self):
        self.log.info('Getting role readme')
        readme = markup_utils.get_readme_doc_file(
            os.path.join(self.root, self.rel_path))
        if not readme:
            raise exc.ContentLoadError('No role readme found.')
        self.readme_file = readme.name
        self.readme_html = markup_utils.get_html(readme)

    def _get_metadata_description(self):
        self.log.info('Getting role description')
        pass


def get_loader_cls(content_type):
    if content_type.category == constants.ContentCategory.ROLE:
        return RoleLoader
    elif content_type.category in [constants.ContentCategory.PLUGIN,
                                   constants.ContentCategory.MODULE]:
        return PluginLoader
    return None
