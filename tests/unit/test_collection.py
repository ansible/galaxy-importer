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
import logging
import os
import re
import tarfile
import tempfile
from types import SimpleNamespace
from unittest import mock

import attr
import pytest
import requests

from galaxy_importer import collection
from galaxy_importer.collection import CollectionLoader
from galaxy_importer import config
from galaxy_importer.config import ConfigFile
from galaxy_importer.constants import ContentType
from galaxy_importer import exceptions as exc
from galaxy_importer import schema
from galaxy_importer.utils import markup as markup_utils

log = logging.getLogger(__name__)

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
  "repository": "http://example.com/repository",
  "documentation": null,
  "homepage": null,
  "issues": null
 },
 "file_manifest_file": {
  "name": "FILES.json",
  "ftype": "file",
  "chksum_type": "sha256",
  "chksum_sha256": "dc90402feea54f479780e067cba748559cb01bff52e6724a15264b9a55e8f000",
  "format": 1
 }
}
"""

FILES_JSON = """
{
 "format": 1,
 "files": [
  {
   "name": ".",
   "ftype": "dir",
   "chksum_type": null,
   "chksum_sha256": null,
   "format": 1
  },
  {
   "name": "LICENSE",
   "ftype": "file",
   "chksum_type": "sha256",
   "chksum_sha256": "af995cae1eec804d1c0423888d057eefe492f7d8f06a4672be45112927b37929",
   "format": 1
  },
  {
   "name": "README.md",
   "ftype": "file",
   "chksum_type": "sha256",
   "chksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
   "format": 1
  }
 ]
}
"""

LICENSE_FILE = """
This collection is public domain. No rights Reserved.
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
        shutil.rmtree(tmp_dir)


@pytest.fixture
def populated_collection_root(tmp_collection_root):
    with open(os.path.join(tmp_collection_root, 'MANIFEST.json'), 'w') as fh:
        fh.write(MANIFEST_JSON)
    with open(os.path.join(tmp_collection_root, 'README.md'), 'w'):
        pass
    with open(os.path.join(tmp_collection_root, 'FILES.json'), 'w') as fh:
        fh.write(FILES_JSON)
    with open(os.path.join(tmp_collection_root, 'LICENSE'), 'w') as fh:
        fh.write(LICENSE_FILE)
    return tmp_collection_root


@pytest.fixture
def readme_artifact_file(request):
    marker = request.node.get_closest_marker("sha256")
    sha256 = marker.args[0]
    artifact_file = \
        schema.CollectionArtifactFile(name="README.md",
                                      ftype="file",
                                      chksum_type="sha256",
                                      chksum_sha256=sha256,
                                      format=1)

    return artifact_file


@pytest.mark.sha256("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
def test_check_artifact_file(populated_collection_root, readme_artifact_file):
    res = collection.check_artifact_file(populated_collection_root, readme_artifact_file)
    log.debug('res: %s', res)
    assert res is True


@pytest.mark.sha256("deadbeef98fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
def test_check_artifact_file_bad_chksum(populated_collection_root, readme_artifact_file):
    with pytest.raises(exc.CollectionArtifactFileChecksumError,
                       match=r"File README.md.*but the.*actual sha256sum was.*"):
        collection.check_artifact_file(populated_collection_root, readme_artifact_file)


@mock.patch('galaxy_importer.collection.CollectionLoader._build_docs_blob')
def test_manifest_success(_build_docs_blob, populated_collection_root):
    _build_docs_blob.return_value = {}

    filename = CollectionFilename('my_namespace', 'my_collection', '2.0.2')
    data = CollectionLoader(
        populated_collection_root,
        filename,
        cfg=SimpleNamespace(run_ansible_doc=True),
    ).load()
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
    assert data.metadata.repository == 'http://example.com/repository'
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
        ('"deployment",', '"tag",' * 30, "Expecting no more than 20 tags"),
        ('"A collection with various roles and plugins"', '[]', "be a string"),
        ('"MIT"', '{}', "to be a list of strings"),
        ('"MIT"', '"not-a-valid-license-id"', "list of valid SPDX license"),
        ('"*"', '555', "Expecting depencency version to be string"),
        ('"dave.deploy"', '"davedeploy"', "Invalid dependency format:"),
        ('"dave.deploy"', '"007.deploy"', "Invalid dependency format: '007'"),
        ('"dave.deploy"', '"my_namespace.my_collection"', "self dependency"),
        ('"*"', '"3.4.0.4"', "version spec range invalid"),
        ('"http://example.com/repository"', '["repo"]', "must be a string"),
        ('"http://example.com/repository"', 'null', "'repository' is required"),
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
    collection_loader = CollectionLoader('/tmpdir', 'filename',
                                         cfg=SimpleNamespace(run_ansible_doc=True))
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
    collection_loader = CollectionLoader('/tmpdir', 'filename',
                                         cfg=SimpleNamespace(run_ansible_doc=True))
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

    collection_loader = CollectionLoader('/tmpdir', 'filename',
                                         cfg=SimpleNamespace(run_ansible_doc=False))
    collection_loader.content_objs = []
    res = collection_loader._build_docs_blob()
    assert attr.asdict(res) == {
        'collection_readme': {'name': None,
                              'html': None},
        'documentation_files': [],
        'contents': [],
    }


@mock.patch('galaxy_importer.utils.markup.get_readme_doc_file')
def test_build_docs_blob_no_readme(get_readme_doc_file):
    get_readme_doc_file.return_value = None
    collection_loader = CollectionLoader('/tmpdir', 'filename',
                                         cfg=SimpleNamespace(run_ansible_doc=True))
    collection_loader.content_objs = []
    with pytest.raises(exc.ImporterError):
        collection_loader._build_docs_blob()


@mock.patch('galaxy_importer.collection.CollectionLoader._build_docs_blob')
def test_filename_empty_value(_build_docs_blob, populated_collection_root):
    _build_docs_blob.return_value = {}

    filename = CollectionFilename(
        namespace='my_namespace',
        name='my_collection',
        version=None)
    data = CollectionLoader(
        populated_collection_root,
        filename,
        cfg=SimpleNamespace(run_ansible_doc=True),
    ).load()
    assert data.metadata.namespace == 'my_namespace'
    assert data.metadata.name == 'my_collection'
    assert data.metadata.version == '2.0.2'


@mock.patch('galaxy_importer.collection.CollectionLoader._build_docs_blob')
def test_filename_none(_build_docs_blob, populated_collection_root):
    _build_docs_blob.return_value = {}

    filename = None
    data = CollectionLoader(
        populated_collection_root,
        filename,
        cfg=SimpleNamespace(run_ansible_doc=True),
    ).load()
    assert data.metadata.namespace == 'my_namespace'
    assert data.metadata.name == 'my_collection'
    assert data.metadata.version == '2.0.2'


def test_filename_not_match_metadata(populated_collection_root):
    filename = CollectionFilename('diff_ns', 'my_collection', '2.0.2')
    with pytest.raises(exc.ManifestValidationError):
        CollectionLoader(populated_collection_root, filename).load()


def test_license_file(populated_collection_root):
    with open(os.path.join(populated_collection_root, 'MANIFEST.json'), 'w') as fh:
        manifest = json.loads(MANIFEST_JSON)
        manifest['collection_info']['license'] = []
        manifest['collection_info']['license_file'] = 'LICENSE'
        fh.write(json.dumps(manifest))

    data = CollectionLoader(
        populated_collection_root,
        filename=None,
        cfg=SimpleNamespace(run_ansible_doc=True),
    ).load()
    assert data.metadata.license_file == 'LICENSE'


def test_missing_readme(populated_collection_root):
    os.unlink(os.path.join(populated_collection_root, 'README.md'))

    with pytest.raises(
        exc.CollectionArtifactFileNotFound,
        match=re.escape(r"The file (README.md) was not found")
    ) as excinfo:
        CollectionLoader(populated_collection_root, filename=None).load()
    assert 'README.md' == excinfo.value.missing_file


def test_manifest_json_with_no_files_json_info(populated_collection_root):
    # Modify MANIFEST.json so it doesn't reference a FILES.json
    manifest_json_obj = json.loads(MANIFEST_JSON)
    del manifest_json_obj['file_manifest_file']
    with open(os.path.join(populated_collection_root, 'MANIFEST.json'), 'w') as fh:
        fh.write(json.dumps(manifest_json_obj))

    # MANIFEST.json did not contain a 'file_manifest_file' item pointing to FILES.json
    msg_match = "MANIFEST.json did not contain a 'file_manifest_file' item pointing to FILES.json"
    with pytest.raises(exc.ManifestValidationError,
                       match=msg_match) as excinfo:

        CollectionLoader(populated_collection_root, filename=None).load()

    # pytest.raises ensures the outer exeption is a ManifestValidationError, this
    # asserts that the inner exceptions are a ValueError and a KeyError
    assert isinstance(excinfo.value.__cause__, ValueError)
    assert isinstance(excinfo.value.__cause__.__cause__, KeyError)


def test_unaccounted_for_files(populated_collection_root):
    extras = ['whatever.py.finalVerForReal',
              'a.out',
              'debug.log',
              '.oops-a-secret']
    for extra in extras:
        with open(os.path.join(populated_collection_root, extra), 'w'):
            pass

    filename = None
    with pytest.raises(exc.FileNotInFileManifestError,
                       match='Files in the artifact but not the file manifest:') as excinfo:
        CollectionLoader(
            populated_collection_root,
            filename,
            cfg=SimpleNamespace(run_ansible_doc=True),
        ).load()
    assert 'a.out' in excinfo.value.unexpected_files


def test_import_collection(mocker):
    mocker.patch.object(collection, '_import_collection')
    mocker.patch.object(ConfigFile, 'load')
    collection.import_collection(file=None, logger=logging, cfg=None)
    assert ConfigFile.load.called
    assert collection._import_collection.called


@pytest.fixture
def mock__import_collection(mocker):
    mocker.patch.object(collection, 'CollectionLoader')
    mocked_runners = mocker.patch.object(collection, 'runners')
    mocked_attr = mocker.patch.object(collection, 'attr')
    mocked_runners.get_runner.return_value = False
    mocked_attr.asdict.return_value = None


def test__import_collection(mocker, tmp_collection_root, mock__import_collection):
    mocker.patch.object(collection, 'subprocess')
    cfg = config.Config(config_data=config.ConfigFile.load())
    with open(os.path.join(tmp_collection_root, 'test_file.tar.gz'), 'w') as f:
        collection._import_collection(file=f, filename='', file_url=None, logger=logging, cfg=cfg)
    assert collection.subprocess.run.called


def test_download_archive(mocker, tmp_collection_root):
    mocked_get = mocker.patch.object(requests, 'get')
    mocked_get.return_value = SimpleNamespace(content=b'my_file_contents')
    filepath = collection._download_archive('file_url', tmp_collection_root)
    with open(filepath) as f:
        assert f.read() == 'my_file_contents'


def test_extract_archive(tmp_collection_root):
    tar_path = os.path.join(tmp_collection_root, 'test_archive.tar.gz')
    extract_path = os.path.join(tmp_collection_root, 'extract')
    os.makedirs(extract_path)

    with tarfile.open(tar_path, 'w') as tar:
        galaxy_yml_path = os.path.join(tmp_collection_root, 'galaxy.yml')
        with open(galaxy_yml_path, 'w'):
            pass
        tar.add(galaxy_yml_path, arcname='galaxy.yml')

    assert not os.path.isfile(os.path.join(extract_path, 'galaxy.yml'))
    collection._extract_archive(
        tarfile_path=tar_path,
        extract_dir=extract_path,
    )
    assert os.path.isfile(os.path.join(extract_path, 'galaxy.yml'))


def test_extract_archive_bad_tarfile_path_name(mock__import_collection):
    with pytest.raises(exc.ImporterError, match='Cannot open: No such file or directory'):
        collection._extract_archive(
            tarfile_path='file-does-not-exist.tar.gz',
            extract_dir='/',
        )


def test_extract_archive_bad_tarfile_path_dir():
    with pytest.raises(exc.ImporterError, match='Errno 2] No such file or directory'):
        collection._extract_archive(
            tarfile_path='dir-does-not-exist/file.tar.gz',
            extract_dir='/',
        )
