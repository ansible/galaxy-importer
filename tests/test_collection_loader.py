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
import tempfile

from galaxy_importer.collection import CollectionLoader
from galaxy_importer.exceptions import ManifestValidationError


MANIFEST_JSON = """
{
 "collection_info": {
  "namespace": "my_namespace",
  "name": "my_collection",
  "version": "2.0.2",
  "authors": [
   "John Doe"
  ],
  "readme": "README.md",
  "tags": [
   "deployment",
   "fedora"
  ],
  "description": "A collection with various roles and plugins",
  "license": [
   "GPL-3.0-or-later",
   "MIT"
  ],
  "license_file": null,
  "dependencies": {
   "my_namespace.collection_nginx": ">=0.1.6",
   "network_user.collection_inspect": "2.0.0",
   "dave.deploy": "*"
  },
  "repository": null,
  "documentation": null,
  "homepage": null,
  "issues": null
 }
}
"""


def test_manifest_success():
    with tempfile.TemporaryDirectory() as temp_dir:
        with open(os.path.join(temp_dir, 'MANIFEST.json'), 'w') as fh:
            fh.write(MANIFEST_JSON)

        data = CollectionLoader(
            temp_dir, 'my_namespace-my_collection-2.0.2.tar.gz').load()
        assert data['metadata']['namespace'] == 'my_namespace'
        assert data['metadata']['name'] == 'my_collection'
        assert data['metadata']['version'] == '2.0.2'
        assert data['metadata']['authors'] == ['John Doe']
        assert data['metadata']['readme'] == 'README.md'
        assert data['metadata']['tags'] == ['deployment', 'fedora']
        assert data['metadata']['description'] == \
            'A collection with various roles and plugins'
        assert data['metadata']['license_file'] is None
        assert data['metadata']['dependencies'] == {
            'my_namespace.collection_nginx': '>=0.1.6',
            'network_user.collection_inspect': '2.0.0',
            'dave.deploy': '*'
        }
        assert data['metadata']['repository'] is None
        assert data['metadata']['homepage'] is None
        assert data['metadata']['issues'] is None
        assert data['error'] is None
        assert data['result'] == 'completed'


@pytest.mark.parametrize(
    'manifest_text,new_text,error_subset',
    [
        ('my_namespace', '', "'namespace' is required"),
        ('my_namespace', '00my.name.space', "'namespace' has invalid format"),
        ('my_collection', '', "'name' is required"),
        ('my_collection', '_my_collection', "'name' has invalid format"),
        ('2.0.2', '', "'version' is required"),
        ('2.0.2', '2.2.0.0.2', "semantic version format"),
        ('"John Doe"', '', "'authors' is required"),
        ('[\n   "John Doe"\n  ]', '"John Doe"', "to be a list of strings"),
        ('README.md', '', "'readme' is required"),
        ('"fedora"', '["fedora"]', "to be a list of strings"),
        ('"deployment",', '"tag",'*30, "Expecting no more than 20 tags"),
        ('"A collection with various roles and plugins"', '[]', "be a string"),
        ('"MIT"', '{}', "to be a list of strings"),
        ('"MIT"', '"not-a-valid-license-id"', "list of valid SPDX license"),
        ('"*"', '555', "Expecting depencency version to be string"),
        ('"dave.deploy"', '"davedeploy"', "Invalid dependency format:"),
        ('"dave.deploy"', '"007.deploy"', "Invalid dependency format: '007'"),
        ('"dave.deploy"', '"my_namespace.my_collection"', "self dependency"),
        ('"*"', '"3.4.0.4"', "version spec range invalid"),
        ('"repository": null', '"repository": []', "must be a string"),
        ('"documentation": null', '"documentation": []', "must be a string"),
        ('"homepage": null', '"homepage": []', "must be a string"),
        ('"issues": null', '"issues": []', "must be a string"),
    ],
)
def test_manifest_fail(manifest_text, new_text, error_subset):
    manifest_edited = MANIFEST_JSON.replace(manifest_text, new_text)
    with tempfile.TemporaryDirectory() as temp_dir:
        with open(os.path.join(temp_dir, 'MANIFEST.json'), 'w') as fh:
            fh.write(manifest_edited)

        with pytest.raises(ManifestValidationError,
                           match=error_subset):
            CollectionLoader(
                temp_dir, 'my_namespace-my_collection-2.0.2.tar.gz').load()
