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

import os
import pytest

from galaxy_importer.schema import CollectionInfo
from galaxy_importer import config


@pytest.fixture
def collection_info():
    metadata = {
        'namespace': 'acme',
        'name': 'jenkins',
        'version': '3.5.0',
        'license': ['MIT'],
        'readme': 'README.md',
        'authors': ['Bob Smith <b.smith@acme.com>'],
        'tags': ['application'],
        'repository': 'http://example.com/repository',
    }
    return metadata


def test_collection_info(collection_info):
    res = CollectionInfo(**collection_info)
    assert type(res) == CollectionInfo
    assert res.namespace == 'acme'
    assert res.name == 'jenkins'
    assert res.version == '3.5.0'
    assert res.license == ['MIT']
    assert res.readme == 'README.md'
    assert res.authors == ['Bob Smith <b.smith@acme.com>']
    assert res.tags == ['application']
    assert res.repository == 'http://example.com/repository'


def test_readme_req(collection_info):
    collection_info['readme'] = ''
    with pytest.raises(ValueError, match=r"'readme' is required"):
        CollectionInfo(**collection_info)


def test_repo_req(collection_info):
    collection_info['repository'] = ''
    with pytest.raises(ValueError, match=r"'repository' is required"):
        CollectionInfo(**collection_info)


@pytest.mark.parametrize(
    'valid_name',
    [
        'my_namespace',
        'my_name',
        'roles75',
        'nginx',
        'nginx_',
        'deploy4py_script',
    ]
)
def test_valid_names(collection_info, valid_name):
    collection_info['name'] = valid_name
    res = CollectionInfo(**collection_info)
    assert res.name == valid_name


@pytest.mark.parametrize(
    'invalid_name',
    [
        '_leading_underscore',
        'has-some-dashes',
        '5tarts_with_number',
        '030',
        '0x4e3',
        'has space',
        'hasUpperCase',
        'double__under',
        'invalid#char',
        'inv@lid/char',
        'no.dots',
    ]
)
def test_invalid_names(collection_info, invalid_name):
    collection_info['name'] = invalid_name
    with pytest.raises(ValueError, match=r"'name' has invalid format"):
        CollectionInfo(**collection_info)


@pytest.mark.parametrize(
    'valid_tags',
    [
        ['application', 'good_tag', 'goodtag'],
        ['application', 'deployment'],
        ['application', 'fedora'],
        ['application', 'fedora29'],
        ['application', 'fedora_29'],
        ['application', 'alloneword'],
        ['application', 'deployment', 'fedora', 'a_007', 'alloneword']
    ]
)
def test_valid_tags(collection_info, valid_tags):
    collection_info['tags'] = valid_tags
    res = CollectionInfo(**collection_info)
    assert res.tags == valid_tags


@pytest.mark.parametrize(
    'invalid_tags',
    [
        ['007'],
        ['4ubuntu'],
        ['0x4e3'],
        ['bad-tag'],
        ['Badtag'],
        ['badTAG'],
        ['bad-tag', 'goodtag'],
        ['bad tag'],
        ['bad.tag'],
        ['bad.tag', 'bad tag'],
        ['_deploy'],
        ['inv@lid/char'],
    ]
)
def test_invalid_tags(collection_info, invalid_tags):
    collection_info['tags'] = invalid_tags
    with pytest.raises(ValueError, match="'tag' has invalid format"):
        CollectionInfo(**collection_info)


def test_max_tags(collection_info):
    collection_info['tags'] = [str(f'tag_{i}') for i in range(91, 110)]
    collection_info['tags'].insert(0, 'application')
    res = CollectionInfo(**collection_info)
    arr = [str(f'tag_{i}') for i in range(91, 110)]
    arr.insert(0, 'application')
    assert arr == res.tags

    collection_info['tags'] = [str(f'tag_{i}') for i in range(91, 111)]
    collection_info['tags'].insert(0, 'application')
    with pytest.raises(ValueError, match=r'Expecting no more than '):
        CollectionInfo(**collection_info)


@pytest.fixture
def temp_config_file():
    try:
        dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        config_file = os.path.join(dir, 'galaxy_importer', 'galaxy-importer.cfg')
        yield config_file
    finally:
        os.remove(config_file)


def test_required_tag(collection_info, temp_config_file):
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nCHECK_REQUIRED_TAGS = True')
        f.flush()
        config_data = config.ConfigFile.load()
        config.Config(config_data=config_data)
        collection_info['tags'] = ['fail']
        with pytest.raises(ValueError, match=r'At least one tag required from tag list: '):
            CollectionInfo(**collection_info)


@pytest.mark.parametrize(
    'valid_semver',
    [
        '1.2.3',
        '1.0.0-beta',
        '2.0.0-rc.2',
        '4.6.21',
        '0.1.1-alpha+build.2012-05-15',
    ]
)
def test_valid_semver(collection_info, valid_semver):
    collection_info['version'] = valid_semver
    res = CollectionInfo(**collection_info)
    assert res.version == valid_semver


@pytest.mark.parametrize(
    'invalid_semver',
    [
        '2',
        '1.2.3a',
        '2.0.02',
        '1.2.beta',
        '3,4',
        '3.4.0.4',
        'latest',
        'v0',
    ]
)
def test_invalid_semver(collection_info, invalid_semver):
    collection_info['version'] = invalid_semver
    with pytest.raises(ValueError,
                       match=r"'version' to be in semantic version"):
        CollectionInfo(**collection_info)


def test_license(collection_info):
    collection_info['license'] = ['MIT', 'GPL-2.0-only', 'Apache-2.0']
    res = CollectionInfo(**collection_info)
    assert res.license == ['MIT', 'GPL-2.0-only', 'Apache-2.0']
    assert res.license_file is None

    collection_info['license'] = ['MIT', 'not-a-real-license', 'n00p']
    with pytest.raises(ValueError, match=r"Expecting 'license' to be a list of valid SPDX"):
        CollectionInfo(**collection_info)

    collection_info['license'] = 'MIT'
    with pytest.raises(ValueError, match=r"'license' to be a list of strings"):
        CollectionInfo(**collection_info)


def test_license_file(collection_info):
    collection_info['license'] = []
    collection_info['license_file'] = 'my_very_own_license.txt'
    res = CollectionInfo(**collection_info)
    assert len(res.license) == 0
    assert res.license_file == 'my_very_own_license.txt'

    collection_info['license_file'] = ['my_very_own_license.txt']
    with pytest.raises(ValueError, match=r"'license_file' must be a string"):
        CollectionInfo(**collection_info)


def test_empty_lic_and_lic_file(collection_info):
    collection_info['license'] = []
    with pytest.raises(ValueError, match=r"'license' or 'license_file' are required"):
        CollectionInfo(**collection_info)


def test_both_lic_and_lic_file(collection_info):
    collection_info['license_file'] = 'my_very_own_license.txt'
    with pytest.raises(
        ValueError,
        match=r"'license' and 'license_file' keys are mutually exclusive"
    ):
        CollectionInfo(**collection_info)


@pytest.mark.parametrize(
    'valid_license_list',
    [
        ['MIT'],
        ['Apache-2.0'],
        ['BSD-3-Clause'],
        ['CC-BY-4.0', 'MIT']
    ]
)
def test_valid_license(collection_info, valid_license_list):
    collection_info['license'] = valid_license_list
    res = CollectionInfo(**collection_info)
    assert res.license == valid_license_list


@pytest.mark.parametrize(
    'invalid_license_list',
    [
        ['BSD'],
        ['Apache'],
        ['MIT AND Apache-2.0'],
        ['something_else'],
        ['CC-BY-4.0', 'MIT', 'bad_license_id']
    ]
)
def test_invalid_license(collection_info, invalid_license_list):
    collection_info['license'] = invalid_license_list
    with pytest.raises(ValueError, match=r'invalid license identifiers'):
        CollectionInfo(**collection_info)


def test_invalid_dep_type(collection_info):
    collection_info['dependencies'] = 'joe.role1: 3'
    with pytest.raises(TypeError,
                       match=r"'dependencies' must be <class 'dict'>"):
        CollectionInfo(**collection_info)


def test_invalid_dep_name(collection_info):
    collection_info['dependencies'] = {3.3: '1.0.0'}
    with pytest.raises(ValueError, match=r'Expecting depencency to be string'):
        CollectionInfo(**collection_info)


def test_invalid_dep_version(collection_info):
    collection_info['dependencies'] = {'joe.role1': 3}
    with pytest.raises(ValueError,
                       match=r'Expecting depencency version to be string'):
        CollectionInfo(**collection_info)


def test_non_null_str_fields(collection_info):
    collection_info['description'] = None
    res = CollectionInfo(**collection_info)
    assert res.description is None

    collection_info['description'] = 'description of the collection'
    res = CollectionInfo(**collection_info)
    assert res.description == 'description of the collection'

    collection_info['description'] = ['should be a string not list']
    with pytest.raises(ValueError, match=r"'description' must be a string"):
        CollectionInfo(**collection_info)


@pytest.mark.parametrize(
    'dependent_collection',
    [
        'no_dot_in_collection',
        'too.many.dots',
        '.too.many.dots',
        'too.many.dots.',
        'empty_name.',
        '.empty_namespace',
        'a_user._leading_underscore',
        '5tarts_with_number.gunicorn',
        'mynamespace.UPPERCASE_COLLECTION',
        'MyNamespace.mixedcase_collection',
        'mynamespace.my-dashed-collection',
        'my-namespace.mydashedcollection',
        'mynamespace.my spaced collection',
        'my namespace.myspacedcollection',
    ]
)
def test_invalid_dep_format(collection_info, dependent_collection):
    collection_info['dependencies'] = {dependent_collection: '1.0.0'}
    with pytest.raises(ValueError, match=r'Invalid dependency format'):
        CollectionInfo(**collection_info)


@pytest.mark.parametrize(
    'depencency',
    [
        {'alice.apache': 'bad_version'},
        {'alice.apache': ''},
        {'alice.apache': '>=1.0.0, <=2.0.0'},
        {'alice.apache': '>1 <2'},
    ]
)
def test_invalid_version_spec(collection_info, depencency):
    collection_info['dependencies'] = depencency
    with pytest.raises(ValueError, match='version spec range invalid'):
        CollectionInfo(**collection_info)


def test_self_dependency(collection_info):
    namespace = collection_info['namespace']
    name = collection_info['name']
    collection_info['dependencies'] = {
        '{}.{}'.format(namespace, name): '1.0.0'
    }
    with pytest.raises(ValueError, match=r'Cannot have self dependency'):
        CollectionInfo(**collection_info)
