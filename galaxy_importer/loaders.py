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
import shutil
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
ANSIBLE_DOC_PLUGIN_MAP = {'module': 'modules'}
ANSIBLE_DOC_KEYS = ['doc', 'metadata', 'examples', 'return']
ANSIBLE_LINT_EXCEPTION_RETURN_CODE = 1
ROLE_META_FILES = ['meta/main.yml', 'meta/main.yaml', 'meta.yml', 'meta.yaml']
FLAKE8_MAX_LINE_LENGTH = 160
FLAKE8_IGNORE_ERRORS = 'E402'
FLAKE8_SELECT_ERRORS = 'E,F,W'


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
        self.log.info(f'Loading {self.content_type.value} {self.path_name}')


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
        self.log.info(f'Linting {self.content_type.value} {self.path_name} via flake8...')

        if not shutil.which('flake8'):
            self.log.warning('flake8 not found, skipping')
            return

        cmd = [
            'flake8', '--exit-zero', '--isolated',
            '--extend-ignore', FLAKE8_IGNORE_ERRORS,
            '--select', FLAKE8_SELECT_ERRORS,
            '--max-line-length', str(FLAKE8_MAX_LINE_LENGTH),
            '--', self.rel_path,
        ]

        self.log.debug('CMD: ' + ' '.join(cmd))
        proc = Popen(
            cmd,
            cwd=self.root,
            encoding='utf-8',
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
        return '.'.join(list(dirname_parts) + [name])


class DocStringLoader():
    """Process ansible-doc doc strings for entire collection.

    Load by calling ansible-doc once in batch for each plugin type."""
    def __init__(self, path, fq_collection_name, logger=None):
        self.path = path
        self.fq_collection_name = fq_collection_name
        self.log = logger or default_logger

    def load(self):
        self.log.info('Getting doc strings via ansible-doc')
        docs = {}

        if not shutil.which('ansible-doc'):
            self.log.warning('ansible-doc not found, skipping loading of docstrings')
            return docs

        for plugin_type in ANSIBLE_DOC_SUPPORTED_TYPES:
            plugin_dir_name = ANSIBLE_DOC_PLUGIN_MAP.get(plugin_type, plugin_type)

            plugins = self._get_plugins(os.path.join(self.path, 'plugins', plugin_dir_name))

            if not plugins:
                continue

            data = self._run_ansible_doc(plugin_type, plugins)
            data = self._process_doc_strings(data)
            docs[plugin_type] = data

        return docs

    def _get_plugins(self, plugin_dir):
        """Get list of fully qualified plugin names inside directory.

        Ex: ['google.gcp.service_facts', 'google.gcp.storage.subdir2.gc_storage']
        """
        plugins = []
        for root, _, files in os.walk(plugin_dir):
            for filename in files:
                if not filename.endswith('.py') or filename == '__init__.py':
                    continue
                file_path = os.path.join(root, filename)
                sub_dirs = os.path.relpath(root, plugin_dir)

                fq_name_parts = [self.fq_collection_name]
                if sub_dirs and sub_dirs != '.':
                    fq_name_parts.extend(sub_dirs.split('/'))
                fq_name_parts.append(os.path.basename(file_path)[:-3])

                plugins.append('.'.join(fq_name_parts))
        return plugins

    def _run_ansible_doc(self, plugin_type, plugins):
        collections_path = '/'.join(self.path.split('/')[:-3])
        cmd = [
            '/usr/bin/env', f'ANSIBLE_COLLECTIONS_PATHS={collections_path}',
            'ansible-doc',
            '--type', plugin_type,
            '--json',
        ] + plugins
        self.log.debug('CMD: {}'.format(' '.join(cmd)))
        proc = Popen(cmd, cwd=collections_path, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode:
            self.log.error('Error running ansible-doc: cmd="{cmd}" returncode="{rc}" {err}'.format(
                cmd=' '.join(cmd), rc=proc.returncode, err=stderr
            ))
            return {}
        return json.loads(stdout)

    def _process_doc_strings(self, doc_strings):
        processed_doc_strings = {}
        for plugin_key, value in doc_strings.items():
            processed_doc_strings[plugin_key] = self._transform_doc_strings(value, self.log)
        return processed_doc_strings

    @staticmethod
    def _transform_doc_strings(data, logger=default_logger):
        """Transform data meant for UI tables into format suitable for UI."""

        def dict_to_named_list(dict_of_dict):
            """Return new list of dicts for given dict of dicts."""
            try:
                return [
                    {'name': key, **deepcopy(dict_of_dict[key])} for
                    key in dict_of_dict.keys()
                ]
            except TypeError:
                logger.warning(f'Expected this to be a dictionary of dictionaries: {dict_of_dict}')
                return [
                    {'name': key, **deepcopy(dict_of_dict[key])} for
                    key in dict_of_dict.keys()
                    if isinstance(key, dict)
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
        description = self._get_metadata_description()
        readme = self._get_readme()

        if self.cfg.run_ansible_lint:
            for line in self._lint_role(self.rel_path):
                self.log.warning(line)

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
        self.log.info(f'Linting role {self.path_name} via ansible-lint...')

        if not shutil.which('ansible-lint'):
            self.log.warning('ansible-lint not found, skipping lint of role')
            return

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
        readme = markup_utils.get_readme_doc_file(
            os.path.join(self.root, self.rel_path))
        if not readme:
            raise exc.ContentLoadError('No role readme found.')
        return readme

    def _get_metadata_description(self):
        description = None
        meta_path = self._find_metadata_file_path(self.root, self.rel_path)

        if not meta_path:
            self.log.warning('Could not get role description, no role metadata found')
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
    def _find_metadata_file_path(root, rel_path):
        """Gets path to role metadata file."""
        for file in ROLE_META_FILES:
            meta_path = os.path.join(root, rel_path, file)
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
