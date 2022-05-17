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

from git import Repo
import pytest

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
    mocked_runners.get_runner.return_value = mocker.stub()
    mocked_attr.asdict.return_value = None


def test__import_collection(mocker, tmp_collection_root, mock__import_collection):
    mocker.patch.object(collection, "_extract_archive")
    cfg = config.Config(config_data=config.ConfigFile.load())
    with open(os.path.join(tmp_collection_root, "test_file.tar.gz"), "ab") as f:
        pass
    with open(os.path.join(tmp_collection_root, "test_file.tar.gz"), "rb") as f:
        collection._import_collection(file=f, filename="", file_url=None, logger=logging, cfg=cfg)
    assert collection._extract_archive.called


def test__build_collection(tmp_collection_root):
    git_url = "https://github.com/openshift/community.okd.git"
    Repo.clone_from(git_url, tmp_collection_root, depth=1)
    filepath = collection._build_collection(tmp_collection_root, tmp_collection_root)
    assert "community-okd" in filepath

    with pytest.raises(exc.ImporterError, match="file .+ already exists"):
        collection._build_collection(tmp_collection_root, tmp_collection_root)


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
    with open(tar_path, "rb") as fileobj:
        collection._extract_archive(
            fileobj=fileobj,
            extract_dir=extract_path,
        )
    assert os.path.isfile(os.path.join(extract_path, "galaxy.yml"))
