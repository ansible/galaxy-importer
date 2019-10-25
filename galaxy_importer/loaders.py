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
import yaml

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
ROLE_META_FILES = ['meta/main.yml', 'meta/main.yaml', 'meta.yml', 'meta.yaml']


class ContentLoader(metaclass=abc.ABCMeta):

    def __init__(self, content_type, rel_path, root, logger=None):
        """
        :param content_type: Content type.
        :param rel_path: Path to content file or dir, relative to root path.
        :param root: Collection root path.
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
    def _get_tmp_dir(root):
        root_parts = Path(root).parts
        return os.path.join(*root_parts[:3])

    @staticmethod
    def _get_fq_collection_name(root):
        root_parts = Path(root).parts
        return '{}.{}'.format(*root_parts[-2:])

    def _get_fq_name(self, root, path_name):
        return '{}.{}'.format(
            self._get_fq_collection_name(root),
            path_name,
        )

    def _validate_name(self):
        if not re.match(constants.CONTENT_NAME_REGEXP, self.name):
            raise exc.ContentNameError(
                f'{self.content_type.value} name invalid format: {self.name}')

    def _log_loading(self):
        self.log.info(' ')
        self.log.info(
            f'===== LOADING {self.content_type.name}: {self.path_name} =====')


class PluginLoader(ContentLoader):
    def load(self):
        self._log_loading()
        doc_strings = DocStringLoader(
            content_type=self.content_type.value,
            path=self._get_tmp_dir(self.root),
            fq_name=self._get_fq_name(self.root, self.path_name),
            logger=self.log,
        ).load()

        return schema.Content(
            name=self.path_name,
            content_type=self.content_type,
            doc_strings=doc_strings,
        )

    @staticmethod
    def _make_name(rel_path):
        return os.path.splitext(os.path.basename(rel_path))[0]

    @staticmethod
    def _make_path_name(rel_path, name):
        dirname_parts = Path(os.path.dirname(rel_path)).parts[2:]
        return '.'.join(list(dirname_parts) + [name])


class DocStringLoader():
    def __init__(self, content_type, path, fq_name, logger=None):
        self.content_type = content_type
        self.path = path
        self.fq_name = fq_name
        self.log = logger or default_logger

    def load(self):
        if self.content_type not in ANSIBLE_DOC_SUPPORTED_TYPES:
            return None

        self.log.info('Getting doc strings via ansible-doc')
        json_output = self._run_ansible_doc()

        if not json_output:
            return None

        data = json.loads(json_output)
        if not isinstance(data, dict):
            self.log.error('ansible-doc output not dictionary as expected')
            return None
        if len(data.keys()) != 1:
            self.log.error('ansible-doc output did not return single top-level key')
            return None
        data = list(data.values())[0]
        data = self._transform_doc_strings(data)

        return {
            key: data.get(key, None)
            for key in ANSIBLE_DOC_KEYS
        }

    def _run_ansible_doc(self):
        cmd = [
            'env', f'ANSIBLE_COLLECTIONS_PATHS={self.path}',
            'ansible-doc',
            self.fq_name,
            '--type', self.content_type,
            '--json',
        ]
        self.log.debug('CMD: {}'.format(' '.join(cmd)))
        proc = Popen(cmd, cwd=self.path, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode:
            self.log.error(f'Error running ansible-doc: returncode={proc.returncode} {stderr}')
            return None
        return stdout

    @staticmethod
    def _transform_doc_strings(data):
        """Transform data meant for UI tables into format suitable for UI."""

        def dict_to_named_list(dict_of_dict):
            """Return new list of dicts for given dict of dicts."""
            return [
                {'name': key, **deepcopy(dict_of_dict[key])} for
                key in dict_of_dict.keys()
            ]

        def handle_nested_tables(obj, table_key):
            """Recurse over dict to replace nested tables with updated format."""
            if table_key in obj.keys() and isinstance(obj[table_key], dict):
                obj[table_key] = dict_to_named_list(obj[table_key])
                for row in obj[table_key]:
                    handle_nested_tables(row, table_key)

        doc = data.get('doc', {})
        if isinstance(doc.get('options'), dict):
            doc['options'] = dict_to_named_list(doc['options'])
            for d in doc['options']:
                handle_nested_tables(d, table_key='suboptions')

        ret = data.get('return', None)
        if ret and isinstance(ret, dict):
            data['return'] = dict_to_named_list(ret)
            for d in data['return']:
                handle_nested_tables(d, table_key='contains')

        return data


class RoleLoader(ContentLoader):
    def load(self):
        self._log_loading()
        for line in self._lint_role(self.rel_path):
            self.log.warning(line)
        readme = self._get_readme()
        description = self._get_metadata_description()

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
        return '.'.join(list(dirname_parts) + [name])

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
        return readme

    def _get_metadata_description(self):
        self.log.info('Getting role description')
        description = None
        meta_path = self._find_metadata_file_path(self.rel_path)

        if not meta_path:
            self.log.warning('No role metadata found')
            return description

        with open(meta_path) as fp:
            try:
                role_metadata = yaml.safe_load(fp)
            except Exception:
                self.log.error('Error during parsing of role metadata')
        try:
            description = role_metadata['galaxy_info']['description']
        except KeyError:
            self.log.warning('No role description found in role metadata')
        return description

    @staticmethod
    def _find_metadata_file_path(rel_path):
        """Gets path to role metadata file."""
        for file in ROLE_META_FILES:
            meta_path = os.path.join(rel_path, file)
            if os.path.exists(meta_path):
                return meta_path
        return None


def get_loader_cls(content_type):
    if content_type.category == constants.ContentCategory.ROLE:
        return RoleLoader
    elif content_type.category in [constants.ContentCategory.PLUGIN,
                                   constants.ContentCategory.MODULE]:
        return PluginLoader
    return None
