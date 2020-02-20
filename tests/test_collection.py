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

from collections import namedtuple
import json
import os
import tempfile
from unittest import mock

import attr
import pytest

from galaxy_importer import collection
from galaxy_importer.collection import CollectionLoader
from galaxy_importer.config import ConfigFile
from galaxy_importer.constants import ContentType
from galaxy_importer import exceptions as exc
from galaxy_importer import schema
from galaxy_importer.utils import markup as markup_utils


CollectionFilename = \
    namedtuple("CollectionFilename", ["namespace", "name", "version"])

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


@pytest.fixture
def tmp_collection_root():
    import shutil
    try:
        tmp_dir = tempfile.TemporaryDirectory().name
        sub_path = 'ansible_collections/placeholder_namespace/placeholder_name'
        collection_root = os.path.join(tmp_dir, sub_path)
        os.makedirs(collection_root)
        yield collection_root
    finally:
        # TODO: check if this applies to dir not just file
        shutil.rmtree(tmp_dir)


@mock.patch('galaxy_importer.collection.CollectionLoader._build_docs_blob')
def test_manifest_success(_build_docs_blob, tmp_collection_root):
    _build_docs_blob.return_value = {}
    with open(os.path.join(tmp_collection_root, 'MANIFEST.json'), 'w') as fh:
        fh.write(MANIFEST_JSON)

    with open(os.path.join(tmp_collection_root, 'README.md'), 'w'):
        pass

    filename = CollectionFilename('my_namespace', 'my_collection', '2.0.2')
    data = CollectionLoader(tmp_collection_root, filename).load()
    assert data.metadata.namespace == 'my_namespace'
    assert data.metadata.name == 'my_collection'
    assert data.metadata.version == '2.0.2'
    assert data.metadata.authors == ['John Doe']
    assert data.metadata.readme == 'README.md'
    assert data.metadata.tags == ['deployment', 'fedora']
    assert data.metadata.description == \
        'A collection with various roles and plugins'
    assert data.metadata.license_file is None
    assert data.metadata.dependencies == {
        'my_namespace.collection_nginx': '>=0.1.6',
        'network_user.collection_inspect': '2.0.0',
        'dave.deploy': '*'
    }
    assert data.metadata.repository is None
    assert data.metadata.homepage is None
    assert data.metadata.issues is None


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
def test_manifest_fail(manifest_text, new_text, error_subset, tmp_collection_root):
    manifest_edited = MANIFEST_JSON.replace(manifest_text, new_text)
    with open(os.path.join(tmp_collection_root, 'MANIFEST.json'), 'w') as fh:
        fh.write(manifest_edited)

    with pytest.raises(exc.ManifestValidationError,
                       match=error_subset):
        CollectionLoader(
            tmp_collection_root, 'my_namespace-my_collection-2.0.2.tar.gz').load()


def test_build_contents_blob():
    collection_loader = CollectionLoader('/tmpdir', 'filename')
    collection_loader.content_objs = [
        schema.Content(name='my_module', content_type=ContentType.MODULE),
        schema.Content(name='my_role', content_type=ContentType.ROLE),
    ]
    res = collection_loader._build_contents_blob()
    assert [attr.asdict(item) for item in res] == [
        {'content_type': 'module', 'description': None, 'name': 'my_module'},
        {'content_type': 'role', 'description': None, 'name': 'my_role'}
    ]


@mock.patch('galaxy_importer.utils.markup.get_html')
@mock.patch('galaxy_importer.utils.markup.get_readme_doc_file')
def test_build_docs_blob_contents(get_readme_doc_file, get_html):
    get_readme_doc_file.return_value.name = 'README.md'
    get_html.return_value = '<p>A detailed guide</p>'
    collection_loader = CollectionLoader('/tmpdir', 'filename')
    collection_loader.content_objs = [
        schema.Content(name='my_module', content_type=ContentType.MODULE),
        schema.Content(name='my_role', content_type=ContentType.ROLE),
    ]
    res = collection_loader._build_docs_blob()
    assert attr.asdict(res) == {
        'collection_readme': {'name': 'README.md',
                              'html': '<p>A detailed guide</p>'},
        'documentation_files': [],
        'contents': [
            {
                'content_name': 'my_module',
                'content_type': 'module',
                'doc_strings': {},
                'readme_file': None,
                'readme_html': None,
            },
            {
                'content_name': 'my_role',
                'content_type': 'role',
                'doc_strings': {},
                'readme_file': None,
                'readme_html': None,
            },
        ],
    }


@mock.patch('galaxy_importer.utils.markup.get_html')
@mock.patch('galaxy_importer.utils.markup.get_readme_doc_file')
@mock.patch('galaxy_importer.utils.markup.get_doc_files')
def test_build_docs_blob_doc_files(get_doc_files, get_readme, get_html):
    get_readme.return_value.name = 'README.md'
    get_html.return_value = '<p>A detailed guide</p>'
    get_doc_files.return_value = [
        markup_utils.DocFile(name='INTRO.md', text='Intro text',
                             mimetype='text/markdown', hash=''),
        markup_utils.DocFile(name='INTRO2.md', text='Intro text',
                             mimetype='text/markdown', hash=''),
    ]
    collection_loader = CollectionLoader('/tmpdir', 'filename')
    collection_loader.content_objs = []
    res = collection_loader._build_docs_blob()
    assert attr.asdict(res) == {
        'collection_readme': {'name': 'README.md',
                              'html': '<p>A detailed guide</p>'},
        'documentation_files': [
            {
                'name': 'INTRO.md',
                'html': '<p>A detailed guide</p>',
            },
            {
                'name': 'INTRO2.md',
                'html': '<p>A detailed guide</p>',
            },
        ],
        'contents': [],
    }


@mock.patch('galaxy_importer.utils.markup.get_readme_doc_file')
def test_build_docs_blob_no_readme(get_readme_doc_file):
    get_readme_doc_file.return_value = None
    collection_loader = CollectionLoader('/tmpdir', 'filename')
    collection_loader.content_objs = []
    with pytest.raises(exc.ImporterError):
        collection_loader._build_docs_blob()


@mock.patch('galaxy_importer.collection.CollectionLoader._build_docs_blob')
def test_filename_empty_value(_build_docs_blob, tmp_collection_root):
    _build_docs_blob.return_value = {}
    with open(os.path.join(tmp_collection_root, 'MANIFEST.json'), 'w') as fh:
        fh.write(MANIFEST_JSON)
    with open(os.path.join(tmp_collection_root, 'README.md'), 'w'):
        pass

    filename = CollectionFilename(
        namespace='my_namespace',
        name='my_collection',
        version=None)
    data = CollectionLoader(tmp_collection_root, filename).load()
    assert data.metadata.namespace == 'my_namespace'
    assert data.metadata.name == 'my_collection'
    assert data.metadata.version == '2.0.2'


@mock.patch('galaxy_importer.collection.CollectionLoader._build_docs_blob')
def test_filename_none(_build_docs_blob, tmp_collection_root):
    _build_docs_blob.return_value = {}
    with open(os.path.join(tmp_collection_root, 'MANIFEST.json'), 'w') as fh:
        fh.write(MANIFEST_JSON)
    with open(os.path.join(tmp_collection_root, 'README.md'), 'w'):
        pass

    filename = None
    data = CollectionLoader(tmp_collection_root, filename).load()
    assert data.metadata.namespace == 'my_namespace'
    assert data.metadata.name == 'my_collection'
    assert data.metadata.version == '2.0.2'


def test_filename_not_match_metadata(tmp_collection_root):
    with open(os.path.join(tmp_collection_root, 'MANIFEST.json'), 'w') as fh:
        fh.write(MANIFEST_JSON)

    filename = CollectionFilename('diff_ns', 'my_collection', '2.0.2')
    with pytest.raises(exc.ManifestValidationError):
        CollectionLoader(tmp_collection_root, filename).load()


def test_license_file(tmp_collection_root):
    with open(os.path.join(tmp_collection_root, 'MANIFEST.json'), 'w') as fh:
        manifest = json.loads(MANIFEST_JSON)
        manifest['collection_info']['license'] = []
        manifest['collection_info']['license_file'] = 'my_license.txt'
        fh.write(json.dumps(manifest))
    with open(os.path.join(tmp_collection_root, 'README.md'), 'w'):
        pass
    with open(os.path.join(tmp_collection_root, 'my_license.txt'), 'w'):
        pass
    data = CollectionLoader(tmp_collection_root, filename=None).load()
    assert data.metadata.license_file == 'my_license.txt'


def test_missing_readme(tmp_collection_root):
    with open(os.path.join(tmp_collection_root, 'MANIFEST.json'), 'w') as fh:
        fh.write(MANIFEST_JSON)
    with pytest.raises(
        exc.ManifestValidationError,
        match=r"Could not find file README.md"
    ):
        CollectionLoader(tmp_collection_root, filename=None).load()


def test_import_collection(mocker):
    mocker.patch.object(collection, '_import_collection')
    mocker.patch.object(ConfigFile, 'load')
    collection.import_collection(file=None, cfg=None)
    assert ConfigFile.load.called
    assert collection._import_collection.called
