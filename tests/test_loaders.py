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

import attr
import json
import os
import pytest
import re
import shutil
import tempfile
from unittest import mock

from galaxy_importer import constants
from galaxy_importer import exceptions as exc
from galaxy_importer import loaders
from galaxy_importer import schema


ANSIBLE_DOC_OUTPUT = """
    {"my_sample_module": {
        "doc": {
            "description": ["Sample module for testing."],
            "short_description": "Sample module for testing",
            "version_added": "2.8",
            "options": {
                "exclude": {
                    "description": ["This is the message to send..."],
                    "required": "true"
                },
                "use_new": {
                    "description": ["Control is passed..."],
                    "version_added": "2.7",
                    "default": "auto"
                }
            }
        },
        "examples": null,
        "metadata": null,
        "return": {
            "message": {
                "description": "The output message the sample module generates"
            },
            "original_message": {
                "description": "The original name param that was passed in",
                "type": "str"
            }
        }
    }}
"""


@pytest.fixture
def loader_module():
    return loaders.PluginLoader(
        content_type=constants.ContentType.MODULE,
        rel_path='plugins/modules/my_sample_module.py',
        root='/tmp/tmpiskt5e2n')


@pytest.fixture
def loader_role():
    return loaders.RoleLoader(
        content_type=constants.ContentType.ROLE,
        rel_path='roles/my_sample_role',
        root=None)


def test_get_loader_cls():
    res = loaders.get_loader_cls(constants.ContentType.MODULE)
    assert issubclass(res, loaders.PluginLoader)
    assert not issubclass(res, loaders.RoleLoader)

    res = loaders.get_loader_cls(constants.ContentType.ROLE)
    assert issubclass(res, loaders.RoleLoader)
    assert not issubclass(res, loaders.PluginLoader)


def test_init_plugin_loader(loader_module):
    assert loader_module.name == 'my_sample_module'


def test_init_role_loader(loader_role):
    assert loader_role.name == 'my_sample_role'


def test_bad_plugin_name():
    with pytest.raises(exc.ContentNameError):
        loaders.PluginLoader(
            content_type=constants.ContentType.MODULE,
            rel_path='plugins/modules/bad-name-dashes.py',
            root='/tmp/tmpiskt5e2n')


def test_bad_role_name():
    with pytest.raises(exc.ContentNameError):
        loaders.RoleLoader(
            content_type=constants.ContentType.ROLE,
            rel_path='roles/bad-name-dashes',
            root='/tmp/tmpiskt5e2n')


@mock.patch.object(loaders.PluginLoader, '_get_doc_strings')
def test_plugin_loader_annotated_type(mocked_get_doc_strings, loader_module):
    mocked_get_doc_strings.return_value = None
    assert loader_module.name == 'my_sample_module'
    res = loader_module.load()
    mocked_get_doc_strings.assert_called_once()
    assert isinstance(res, schema.Content)
    assert isinstance(
        res.content_type, attr.fields(schema.Content).content_type.type)


@mock.patch('galaxy_importer.loaders.Popen')
def test_run_ansible_doc(mocked_popen, loader_module):
    mocked_popen.return_value.communicate.return_value = (
        'expected output', '')
    mocked_popen.return_value.returncode = 0
    res = loader_module._run_ansible_doc()
    assert res == 'expected output'


@mock.patch('galaxy_importer.loaders.Popen')
def test_run_ansible_doc_exception(mocked_popen, loader_module):
    mocked_popen.return_value.communicate.return_value = (
        'output', 'error that causes exception')
    mocked_popen.return_value.returncode = 1
    res = loader_module._run_ansible_doc()
    assert not res


@mock.patch.object(loaders.PluginLoader, '_run_ansible_doc')
def test_get_doc_strings(mocked_run_ansible_doc, loader_module):
    mocked_run_ansible_doc.return_value = ANSIBLE_DOC_OUTPUT
    doc_strings = loader_module._get_doc_strings()

    assert doc_strings['doc']['version_added'] == '2.8'
    assert doc_strings['doc']['description'] == \
        ['Sample module for testing.']


def test_ansible_doc_unsupported_type():
    loader_action = loaders.PluginLoader(
        content_type=constants.ContentType.ACTION_PLUGIN,
        rel_path='plugins/action/my_plugin.py',
        root='/tmp/tmpiskt5e2n')
    assert constants.ContentType.ACTION_PLUGIN.value not in \
        loaders.ANSIBLE_DOC_SUPPORTED_TYPES
    assert not loader_action._get_doc_strings()


def test_ansible_doc_transform_params(loader_module):
    data = json.loads(ANSIBLE_DOC_OUTPUT)
    transformed_data = loader_module._transform_params(data)
    assert transformed_data['my_sample_module']['doc']['options'] == [
        {
            'name': 'exclude',
            'description': ['This is the message to send...'],
            'required': 'true',
        },
        {
            'name': 'use_new',
            'description': ['Control is passed...'],
            'version_added': '2.7',
            'default': 'auto'
        }
    ]
    assert transformed_data['my_sample_module']['return'] == [
        {
            'name': 'message',
            'description': 'The output message the sample module generates'
        },
        {
            'name': 'original_message',
            'description': 'The original name param that was passed in',
            'type': 'str'
        }
    ]


@mock.patch.object(loaders.PluginLoader, '_run_ansible_doc')
def test_load(mocked_run_ansible_doc, loader_module):
    mocked_run_ansible_doc.return_value = ANSIBLE_DOC_OUTPUT
    res = loader_module.load()
    assert isinstance(res, schema.Content)
    assert res.name == 'my_sample_module'
    assert res.content_type == constants.ContentType.MODULE
    assert res.readme_file is None
    assert res.readme_html is None
    assert res.description == 'Sample module for testing'
    assert res.doc_strings['doc']['version_added'] == '2.8'


@mock.patch.object(loaders.PluginLoader, '_run_ansible_doc')
def test_ansible_doc_no_output(mocked_run_ansible_doc, loader_module):
    mocked_run_ansible_doc.return_value = ''
    loader_module._get_doc_strings()
    assert loader_module.doc_strings is None


@mock.patch.object(loaders.PluginLoader, '_run_ansible_doc')
def test_ansible_doc_missing_key(mocked_run_ansible_doc, loader_module):
    ansible_doc_output = """
        {"wrong_key_name": {
            "doc": {
                "description": [
                    "Sample module for testing."
                ]
            }
        }}
    """
    mocked_run_ansible_doc.return_value = ansible_doc_output
    loader_module._get_doc_strings()
    assert loader_module.doc_strings is None


ANSIBLELINT_TASK_OK = """---
- name: Add mongodb repo apt_key
  become: true
  apt_key: keyserver=hkp
  until: result.rc == 0
"""

ANSIBLELINT_TASK_SUDO_WARN = """---
- name: edit vimrc
  sudo: true
  lineinfile:
    path: /etc/vimrc
    line: '# added via ansible'
"""


@pytest.fixture
def temp_root():
    try:
        tmp = tempfile.mkdtemp()
        yield tmp
    finally:
        shutil.rmtree(tmp)


def test_ansiblelint_file(loader_role):
    with tempfile.NamedTemporaryFile('w') as fp:
        fp.write(ANSIBLELINT_TASK_SUDO_WARN)
        fp.flush()
        res = list(loader_role._lint_role(fp.name))
    assert 'deprecated sudo' in ' '.join(res).lower()


def test_ansiblelint_role(temp_root, loader_role):
    task_dir = os.path.join(temp_root, 'tasks')
    os.makedirs(task_dir)
    with open(os.path.join(task_dir, 'main.yml'), 'w') as fp:
        fp.write(ANSIBLELINT_TASK_SUDO_WARN)
        fp.flush()
        res = list(loader_role._lint_role(temp_root))
    assert 'deprecated sudo' in ' '.join(res).lower()
    lint_output_path = re.compile(r'^tmp.+\/tasks\/main\.yml.+$')
    assert re.match(lint_output_path, res[0])


def test_ansiblelint_role_no_warn(temp_root, loader_role):
    task_dir = os.path.join(temp_root, 'tasks')
    os.makedirs(task_dir)
    with open(os.path.join(task_dir, 'main.yml'), 'w') as fp:
        fp.write(ANSIBLELINT_TASK_OK)
        fp.flush()
        res = list(loader_role._lint_role(temp_root))
    assert res == []


@mock.patch('galaxy_importer.loaders.Popen')
def test_ansible_lint_exception(mocked_popen, loader_role):
    mocked_popen.return_value.stdout = ''
    mocked_popen.return_value.wait.return_value = 1
    res = list(loader_role._lint_role('.'))
    assert 'Exception running ansible-lint' in res[0]
