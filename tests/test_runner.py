# (c) 2012-2020, Ansible by Red Hat
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
import subprocess
from types import SimpleNamespace

import pytest

from galaxy_importer import config
from galaxy_importer.ansible_test import runners


@pytest.fixture
def temp_config_file():
    try:
        dir = os.path.dirname(os.path.dirname(__file__))
        config_file = os.path.join(dir, 'galaxy_importer', 'galaxy-importer.cfg')
        yield config_file
    finally:
        os.remove(config_file)


def test_get_runner_no_config_file():
    config_data = config.ConfigFile.load()
    cfg = config.Config(config_data=config_data)
    assert runners.get_runner(cfg) is None


def test_get_runner_ansible_test_local(temp_config_file):
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nRUN_ANSIBLE_TEST = True')
        f.flush()
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        assert runners.get_runner(cfg) == runners.LocalAnsibleTestRunner


def test_get_runner_pulp(temp_config_file):
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nRUN_ANSIBLE_TEST = True\n'
                'INFRA_PULP = True')
        f.flush()
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        assert runners.get_runner(cfg) == runners.LocalImageTestRunner


def test_get_runner_pulp_and_osd(temp_config_file):
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nRUN_ANSIBLE_TEST = True\n'
                'INFRA_PULP = True\nINFRA_OSD = True')
        f.flush()
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        assert runners.get_runner(cfg) == runners.OpenshiftJobTestRunner


def test_ansible_test_runner_run(mocker, temp_config_file):
    mocker.patch.object(runners, 'LocalAnsibleTestRunner')
    mocker.patch.object(runners, 'OpenshiftJobTestRunner')
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nRUN_ANSIBLE_TEST = True\n'
                'INFRA_PULP = True\nINFRA_OSD = True')
        f.flush()
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)

        ansible_test_runner = runners.get_runner(cfg)
        ansible_test_runner().run()
        assert not runners.LocalAnsibleTestRunner.called
        assert runners.OpenshiftJobTestRunner.called


def test_local_run(mocker, caplog):
    mocker.patch.object(subprocess, 'Popen')
    subprocess.Popen.return_value.stdout = ['stdout_result']
    subprocess.Popen.return_value.wait.return_value = 0
    caplog.set_level(logging.INFO)

    metadata = SimpleNamespace(
        namespace='test_ns', name='test_name', version='test_version')
    runner = runners.local_ansible_test.LocalAnsibleTestRunner(metadata=metadata)
    runner.run()

    assert len(caplog.records) == 4
    assert subprocess.Popen.called
    assert 'stdout_result' in str(caplog.records[0])
    assert 'Running ansible-test sanity on test_ns-test_name-test_version' in \
        str(caplog.records[1])
    assert 'stdout_result' in str(caplog.records[3])


def test_local_run_rc_error(mocker, caplog):
    mocker.patch.object(subprocess, 'Popen')
    subprocess.Popen.return_value.stdout = ['stdout_result']
    subprocess.Popen.return_value.wait.return_value = 1
    caplog.set_level(logging.INFO)

    metadata = SimpleNamespace(
        namespace='test_ns', name='test_name', version='test_version')
    runner = runners.local_ansible_test.LocalAnsibleTestRunner(metadata=metadata)
    runner.run()

    assert subprocess.Popen.called
    assert len(caplog.records) == 5
    assert caplog.records[4].levelname == 'ERROR'
    assert 'An exception occurred in ansible-test sanity' in str(caplog.records[4])
