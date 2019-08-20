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
import pytest
from unittest import mock

from galaxy_importer import constants
from galaxy_importer import exceptions as exc
from galaxy_importer import loaders
from galaxy_importer import schema


ANSIBLE_DOC_OUTPUT = """
    {"my_sample_module": {
        "doc": {
            "description": [
                "Sample module for testing."
            ],
            "short_description": "Sample module for testing",
            "version_added": "2.8"
        },
        "examples": null,
        "metadata": null,
        "return": null
    }}
"""


@pytest.fixture
def loader_module():
    return loaders.PluginLoader(
        content_type=constants.ContentType.MODULE,
        rel_path='plugins/modules/my_sample_module.py',
        root='/tmp/tmpiskt5e2n')


def test_get_loader_cls():
    res = loaders.get_loader_cls(constants.ContentType.MODULE)
    assert issubclass(res, loaders.PluginLoader)
    assert not issubclass(res, loaders.RoleLoader)

    res = loaders.get_loader_cls(constants.ContentType.ROLE)
    assert issubclass(res, loaders.RoleLoader)
    assert not issubclass(res, loaders.PluginLoader)


def test_init_plugin_loader(loader_module):
    assert loader_module.name == 'my_sample_module'


def test_init_role_loader():
    loader = loaders.RoleLoader(
        content_type=constants.ContentType.ROLE,
        rel_path='roles/my_sample_role',
        root='/tmp/tmpiskt5e2n')
    assert loader.name == 'my_sample_role'


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

    doc = list(filter(lambda item: item.name == 'doc', doc_strings))[0]
    assert doc.string['version_added'] == '2.8'
    assert doc.string['description'] == ['Sample module for testing.']

    ret = list(filter(lambda item: item.name == 'return', doc_strings))[0]
    assert ret.string is None


def test_ansible_doc_unsupported_type():
    loader_action = loaders.PluginLoader(
        content_type=constants.ContentType.ACTION_PLUGIN,
        rel_path='plugins/action/my_plugin.py',
        root='/tmp/tmpiskt5e2n')
    assert constants.ContentType.ACTION_PLUGIN.value not in \
        loaders.ANSIBLE_DOC_SUPPORTED_TYPES
    assert not loader_action._get_doc_strings()


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
    doc = list(filter(lambda item: item.name == 'doc', res.doc_strings))[0]
    assert doc.string['version_added'] == '2.8'


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
