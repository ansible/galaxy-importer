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

import json
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
   "network_user.deployment": "*"
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

        json_result = CollectionLoader(
            temp_dir, 'my_namespace-my_collection-2.0.2.tar.gz').load()
        data = json.loads(json_result)
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
            'network_user.deployment': '*'
        }
        assert data['metadata']['repository'] is None
        assert data['metadata']['homepage'] is None
        assert data['metadata']['issues'] is None
        assert data['error'] is None
        assert data['result'] == 'completed'


def test_manifest_fail():
    manifest_no_readme = MANIFEST_JSON.replace('README.md', '')
    with tempfile.TemporaryDirectory() as temp_dir:
        with open(os.path.join(temp_dir, 'MANIFEST.json'), 'w') as fh:
            fh.write(manifest_no_readme)

        with pytest.raises(ManifestValidationError,
                           match=r"'readme' is required"):
            CollectionLoader(
                temp_dir, 'my_namespace-my_collection-2.0.2.tar.gz').load()


def test_filename_not_match_manifest():
    with tempfile.TemporaryDirectory() as temp_dir:
        with open(os.path.join(temp_dir, 'MANIFEST.json'), 'w') as fh:
            fh.write(MANIFEST_JSON)

        with pytest.raises(ManifestValidationError,
                           match=r"Filename did not match metadata"):
            CollectionLoader(temp_dir, 'ns-coll-1.2.3.tar.gz').load()
