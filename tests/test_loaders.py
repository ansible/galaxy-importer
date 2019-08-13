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

from galaxy_importer import constants
from galaxy_importer import exceptions as exc
from galaxy_importer import loaders
from galaxy_importer import schema


def test_get_loader_cls():
    res = loaders.get_loader_cls(constants.ContentType.MODULE)
    assert issubclass(res, loaders.PluginLoader)
    assert not issubclass(res, loaders.RoleLoader)

    res = loaders.get_loader_cls(constants.ContentType.ROLE)
    assert issubclass(res, loaders.RoleLoader)
    assert not issubclass(res, loaders.PluginLoader)


def test_init_plugin_loader():
    loader = loaders.PluginLoader(
        content_type=constants.ContentType.MODULE,
        rel_path='plugins/modules/my_sample_module.py',
        root='/tmp/tmpiskt5e2n')
    assert loader.name == 'my_sample_module'


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
            rel_path='plugins/modules/my-sample-module.py',
            root='/tmp/tmpiskt5e2n')


def test_bad_role_name():
    with pytest.raises(exc.ContentNameError):
        loaders.RoleLoader(
            content_type=constants.ContentType.ROLE,
            rel_path='roles/my-sample-role',
            root='/tmp/tmpiskt5e2n')


def test_plugin_loader_annotated_type():
    loader = loaders.PluginLoader(
        content_type=constants.ContentType.MODULE,
        rel_path='plugins/modules/my_sample_module.py',
        root='/tmp/tmpiskt5e2n')
    res = loader.load()
    assert isinstance(res, schema.Content)
    assert isinstance(
        res.content_type, attr.fields(schema.Content).content_type.type)
