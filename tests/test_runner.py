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

import os

import pytest
from pytest_mock import mocker  # noqa F401

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


def test_ansible_test_runner_run(mocker, temp_config_file):  # noqa F811
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
