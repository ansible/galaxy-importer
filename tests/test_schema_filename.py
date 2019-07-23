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

import pytest
import semantic_version

from galaxy_importer import schema

NAMESPACE = 'my_namespace'
NAME = 'my_collection'
VERSION_STR = '4.3.0'

FILENAME_DATA = {
    'namespace': NAMESPACE,
    'name': NAME,
    'version': VERSION_STR,
}


def test_filename_parse():
    filename_str = f'{NAMESPACE}-{NAME}-{VERSION_STR}.tar.gz'
    filename_from_str = schema.CollectionFilename.parse(filename_str)

    filename_from_dict = schema.CollectionFilename(**FILENAME_DATA)

    for filename_obj in [filename_from_str, filename_from_dict]:
        assert str(filename_obj) == filename_str
        assert filename_obj.namespace == NAMESPACE
        assert filename_obj.name == NAME
        assert filename_obj.version == semantic_version.Version(VERSION_STR)


@pytest.mark.parametrize(
    'filename_str',
    [
        f'{NAMESPACE}-{NAME}-{VERSION_STR}.tar.gz',
        f'{NAMESPACE}-{NAME}-0.1.1-alpha+build.2012-05-15.tar.gz',
        pytest.param(f'{NAMESPACE}{NAME}{VERSION_STR}.tar.gz',
                     marks=pytest.mark.xfail),  # 0 dashes
        pytest.param(f'{NAMESPACE}-{NAME}{VERSION_STR}.tar.gz',
                     marks=pytest.mark.xfail),  # 1 dash
        pytest.param(f'{NAMESPACE}-{NAME}-{VERSION_STR}!.tar.gz',
                     marks=pytest.mark.xfail),  # bang
    ],
)
def test_filename_format(filename_str):
    res = schema.CollectionFilename.parse(filename_str)
    assert type(res) == schema.CollectionFilename


@pytest.mark.parametrize(
    'filename_str,error_subset',
    [
        (f'no__dunder-{NAME}-{VERSION_STR}.tar.gz', 'Invalid namespace:'),
        (f'{NAMESPACE}-0startswithnum-{VERSION_STR}.tar.gz', 'Invalid name:'),
    ]
)
def test_bad_name_error(filename_str, error_subset):
    with pytest.raises(ValueError) as excinfo:
        schema.CollectionFilename.parse(filename_str)
    assert error_subset in str(excinfo.value)
