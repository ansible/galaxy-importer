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
import pytest
import shutil

from galaxy_importer.ansible_test.builders.local_image_build import Build
from galaxy_importer import exceptions as exc
from galaxy_importer.ansible_test import runners
from types import SimpleNamespace
from unittest import mock


@pytest.fixture
def build():
    return Build("/file/path/to/archive.tar.gz", "namespace-name-0.0.1", logger=None)


@pytest.fixture
def metadata():
    return SimpleNamespace(namespace="test_ns", name="test_name", version="test_version")


@mock.patch("shutil.which")
def test_runner_run(mocked_shutil_which, metadata, mocker):
    runner = mock.Mock(runners.local_image.LocalImageTestRunner(metadata=metadata))

    mocked_build = mock.Mock(Build)
    mocker.patch.object(mocked_build, "build_image")
    mocker.patch.object(mocked_build, "cleanup")
    mocker.patch.object(mocked_build, "get_container_engine")
    mocker.patch.object(runner, "_run_image")
    Build.get_container_engine.return_value = "podman"
    shutil.which.return_value = True

    runner.run()

    mocked_build.build_image.assert_called()
    runner._run_image.assert_called()
    mocked_build.cleanup.assert_called()
    mocked_build.get_container_engine.assert_called()


@mock.patch("shutil.which")
def test_runner_run_exits(mocked_shutil_which, metadata, mocker, caplog):
    caplog.set_level(logging.WARNING)
    runner = runners.local_image.LocalImageTestRunner(metadata=metadata)

    mocker.patch.object(Build, "build_image")
    mocker.patch.object(Build, "cleanup")
    mocker.patch.object(Build, "get_container_engine")
    mocker.patch.object(runner, "_run_image")
    Build.get_container_engine.return_value = "random_container_engine"
    shutil.which.return_value = False

    runner.run()

    Build.build_image.assert_not_called()
    assert runner._run_image.not_called
    assert Build.cleanup.not_called
    assert Build.get_container_engine.called
    assert '"random_container_engine" not found, skipping ansible-test sanity' in [
        r.message for r in caplog.records
    ]


@mock.patch("galaxy_importer.ansible_test.runners.local_image.Popen")
def test_run_image(mocked_popen, metadata):
    runner = runners.local_image.LocalImageTestRunner(metadata=metadata)
    mocked_popen.return_value.stdout = ["test 1 ran", "test2 ran"]
    mocked_popen.return_value.wait.return_value = 0

    runner._run_image("1234", "podman")

    assert mocked_popen.called


@mock.patch("galaxy_importer.ansible_test.runners.local_image.Popen")
def test_run_image_exception(mocked_popen, metadata):
    runner = runners.local_image.LocalImageTestRunner(metadata=metadata)
    mocked_popen.return_value.stdout = ["test1 ran", "test2 ran"]
    mocked_popen.return_value.wait.return_value = 1

    with pytest.raises(exc.AnsibleTestError):
        runner._run_image("1234", "podman")
