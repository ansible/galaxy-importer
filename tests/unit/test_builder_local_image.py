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
import pytest
import tempfile

from galaxy_importer import config
from galaxy_importer import exceptions as exc
from galaxy_importer.ansible_test.builders.local_image_build import Build
from unittest import mock


@pytest.fixture
def build():
    cfg = config.Config(config_data=config.ConfigFile.load())
    return Build('/file/path/to/archive.tar.gz', 'name', cfg)


@pytest.fixture
def tmp_file():
    try:
        dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        tmp_file = os.path.join(dir, 'galaxy_importer', 'namespace-name-0.0.1.tar.gz')
        yield tmp_file
    finally:
        os.remove(tmp_file)


def test_build_image(mocker, tmp_file, temp_config_file, caplog):
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nLOCAL_IMAGE_DOCKER = False')
        f.flush()
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        caplog.set_level(logging.INFO)
        with open(tmp_file, 'w') as f:
            f.write('file contents go here')
            f.flush()
            build = Build(
                filepath=tmp_file,
                collection_name='namespace-name-version',
                cfg=cfg
            )
            mocker.patch.object(Build, '_build_dockerfile')
            mocker.patch.object(Build, '_copy_collection_file')
            mocker.patch.object(Build, '_build_image_with_artifact')
            _ = build.build_image()
    assert build._build_dockerfile.called
    assert build._copy_collection_file.called
    assert build._build_image_with_artifact.called
    assert 'Building ContainerFile' in [r.message for r in caplog.records]


def test_build_image_dockerfile(mocker, tmp_file, temp_config_file, caplog):
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nLOCAL_IMAGE_DOCKER = True')
        f.flush()
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        caplog.set_level(logging.INFO)
        with open(tmp_file, 'w') as f:
            f.write('file contents go here')
            f.flush()
            build = Build(
                filepath=tmp_file,
                collection_name='namespace-name-version',
                cfg=cfg
            )
            mocker.patch.object(Build, '_build_dockerfile')
            mocker.patch.object(Build, '_copy_collection_file')
            mocker.patch.object(Build, '_build_image_with_artifact')
            _ = build.build_image()
    assert 'Building Dockerfile' in [r.message for r in caplog.records]


@mock.patch('galaxy_importer.ansible_test.builders.local_image_build.run')
def test_cleanup(mocked_run, build):
    build.cleanup()
    assert mocked_run.called


def test_build_dockerfile(mocker):
    with tempfile.TemporaryDirectory() as dir:
        Build._build_dockerfile(dir)
        with open(f'{dir}/Dockerfile') as f:
            assert 'COPY archive.tar.gz /archive/archive.tar.gz' in f.read()


@mock.patch('galaxy_importer.ansible_test.builders.local_image_build.Popen')
def test_build_image_with_artifact(mocked_popen, mocker):
    with tempfile.TemporaryDirectory() as dir:
        mocked_popen.return_value.stdout = ['sha256:1234', 'sha256:5678']
        mocked_popen.return_value.wait.return_value = 0
        result = Build._build_image_with_artifact(dir=dir, container_engine='podman')
        assert mocked_popen.called
        assert '5678' in result


@mock.patch('galaxy_importer.ansible_test.builders.local_image_build.Popen')
def test_build_image_with_artifact_exception(mocked_popen, mocker):
    with tempfile.TemporaryDirectory() as dir:
        mocked_popen.return_value.stdout = ['sha256:1234', 'sha256:5678']
        mocked_popen.return_value.wait.return_value = 1
        with pytest.raises(exc.AnsibleTestError):
            Build._build_image_with_artifact(dir=dir, container_engine='podman')


def test_copy_collection_file():
    with tempfile.TemporaryDirectory() as dir:
        f = tempfile.NamedTemporaryFile(delete=False)
        filepath = f.name
        Build._copy_collection_file(dir, filepath)
        assert os.path.exists(os.path.join(dir, 'archive.tar.gz'))
        os.remove(f.name)


@pytest.fixture
def temp_config_file():
    try:
        dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        config_file = os.path.join(dir, 'galaxy_importer', 'galaxy-importer.cfg')
        yield config_file
    finally:
        os.remove(config_file)


def test_get_container_image_podman(temp_config_file):
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nLOCAL_IMAGE_DOCKER = False')
        f.flush()
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        assert Build.get_container_engine(cfg) == 'podman'


def test_get_container_image_docker(temp_config_file):
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nLOCAL_IMAGE_DOCKER = True')
        f.flush()
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        assert Build.get_container_engine(cfg) == 'docker'
