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

import logging
import os
import tarfile
import tempfile
from types import SimpleNamespace

from git import Repo
import pytest
import requests

from galaxy_importer import collection
from galaxy_importer import config
from galaxy_importer import exceptions as exc

log = logging.getLogger(__name__)


@pytest.fixture
def tmp_collection_root():
    import shutil

    try:
        tmp_dir = tempfile.TemporaryDirectory().name
        sub_path = "ansible_collections/placeholder_namespace/placeholder_name"
        collection_root = os.path.join(tmp_dir, sub_path)
        os.makedirs(collection_root)
        yield collection_root
    finally:
        shutil.rmtree(tmp_dir)


def test_import_collection(mocker):
    mocker.patch.object(collection, "_import_collection")
    mocker.patch.object(config.ConfigFile, "load")
    collection.import_collection(file="file_placeholder", logger=logging, cfg=None)
    assert config.ConfigFile.load.called
    assert collection._import_collection.called


def test_sync_collection(tmp_collection_root):
    git_url = "https://github.com/openshift/community.okd.git"
    Repo.clone_from(git_url, tmp_collection_root, depth=1)
    metadata, filepath = collection.sync_collection(tmp_collection_root, tmp_collection_root)
    assert "community-okd" in filepath


@pytest.fixture
def mock__import_collection(mocker):
    mocker.patch.object(collection, "CollectionLoader")
    mocked_runners = mocker.patch.object(collection, "runners")
    mocked_attr = mocker.patch.object(collection, "attr")
    mocked_runners.get_runner.return_value = False
    mocked_attr.asdict.return_value = None


def test__import_collection(mocker, tmp_collection_root, mock__import_collection):
    mocker.patch.object(collection, "subprocess")
    cfg = config.Config(config_data=config.ConfigFile.load())
    with open(os.path.join(tmp_collection_root, "test_file.tar.gz"), "w") as f:
        collection._import_collection(file=f, filename="", file_url=None, logger=logging, cfg=cfg)
    assert collection.subprocess.run.called


def test__build_collection(tmp_collection_root):
    git_url = "https://github.com/openshift/community.okd.git"
    Repo.clone_from(git_url, tmp_collection_root, depth=1)
    filepath = collection._build_collection(tmp_collection_root, tmp_collection_root)
    assert "community-okd" in filepath

    with pytest.raises(exc.ImporterError, match="file .+ already exists"):
        collection._build_collection(tmp_collection_root, tmp_collection_root)


def test_download_archive(mocker, tmp_collection_root):
    mocked_get = mocker.patch.object(requests, "get")
    mocked_get.return_value = SimpleNamespace(content=b"my_file_contents")
    filepath = collection._download_archive("file_url", tmp_collection_root)
    with open(filepath) as f:
        assert f.read() == "my_file_contents"


def test_extract_archive(tmp_collection_root):
    tar_path = os.path.join(tmp_collection_root, "test_archive.tar.gz")
    extract_path = os.path.join(tmp_collection_root, "extract")
    os.makedirs(extract_path)

    with tarfile.open(tar_path, "w") as tar:
        galaxy_yml_path = os.path.join(tmp_collection_root, "galaxy.yml")
        with open(galaxy_yml_path, "w"):
            pass
        tar.add(galaxy_yml_path, arcname="galaxy.yml")

    assert not os.path.isfile(os.path.join(extract_path, "galaxy.yml"))
    collection._extract_archive(
        tarfile_path=tar_path,
        extract_dir=extract_path,
    )
    assert os.path.isfile(os.path.join(extract_path, "galaxy.yml"))


def test_extract_archive_bad_tarfile_path_name(mock__import_collection):
    with pytest.raises(exc.ImporterError, match="Cannot open: No such file or directory"):
        collection._extract_archive(
            tarfile_path="file-does-not-exist.tar.gz",
            extract_dir="/",
        )


def test_extract_archive_bad_tarfile_path_dir():
    with pytest.raises(exc.ImporterError, match="Errno 2] No such file or directory"):
        collection._extract_archive(
            tarfile_path="dir-does-not-exist/file.tar.gz",
            extract_dir="/",
        )
