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

from galaxy_importer.ansible_test.builders.local_image_build import Build
from galaxy_importer import exceptions as exc
from galaxy_importer.ansible_test import runners
from types import SimpleNamespace
from unittest import mock


@pytest.fixture
def build():
    return Build('/file/path/to/archive.tar.gz', 'namespace-name-0.0.1', logger=None)


@pytest.fixture
def metadata():
    return SimpleNamespace(namespace='test_ns', name='test_name', version='test_version')


def test_runner_run(metadata, mocker):
    runner = runners.local_image.LocalImageTestRunner(metadata=metadata)

    mocker.patch.object(Build, 'build_image')
    mocker.patch.object(Build, 'cleanup')
    mocker.patch.object(runner, '_run_image')

    runner.run()

    assert Build.build_image.called
    assert runner._run_image.called
    assert Build.cleanup.called


@mock.patch('galaxy_importer.ansible_test.runners.local_image.Popen')
def test_run_image(mocked_popen, metadata):
    runner = runners.local_image.LocalImageTestRunner(metadata=metadata)
    mocked_popen.return_value.stdout = ['test 1 ran', 'test2 ran']
    mocked_popen.return_value.wait.return_value = 0

    runner._run_image('galaxy-importer:tag')

    assert mocked_popen.called


@mock.patch('galaxy_importer.ansible_test.runners.local_image.Popen')
def test_run_image_exception(mocked_popen, metadata):
    runner = runners.local_image.LocalImageTestRunner(metadata=metadata)
    mocked_popen.return_value.stdout = ['test1 ran', 'test2 ran']
    mocked_popen.return_value.wait.return_value = 1

    with pytest.raises(exc.AnsibleTestError):
        runner._run_image('galaxy-importer:tag')
