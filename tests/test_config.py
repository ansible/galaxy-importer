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

from galaxy_importer import config


@pytest.fixture
def temp_config_file():
    try:
        dir = os.path.dirname(os.path.dirname(__file__))
        config_file = os.path.join(dir, 'galaxy_importer', 'galaxy-importer.cfg')
        yield config_file
    finally:
        os.remove(config_file)


@pytest.fixture
def temp_config_file_b():
    try:
        dir = os.path.dirname(os.path.dirname(__file__))
        config_file = os.path.join(dir, 'galaxy_importer', 'galaxy-importer-b.cfg')
        yield config_file
    finally:
        os.remove(config_file)


def test_config_set_from_file(temp_config_file):
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nRUN_ANSIBLE_TEST = True\n'
                'INFRA_PULP = True')
        f.flush()
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        assert cfg.log_level_main == 'INFO'
        assert cfg.run_ansible_test is True
        assert cfg.infra_pulp is True
        assert cfg.infra_osd is False


def test_config_set_from_env(temp_config_file_b, monkeypatch):
    with open(temp_config_file_b, 'w') as f:
        f.write('[galaxy-importer]\nRUN_ANSIBLE_TEST = True\n'
                'INFRA_PULP = True')
        f.flush()
        monkeypatch.setenv('GALAXY_IMPORTER_CONFIG', temp_config_file_b)
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        assert cfg.run_ansible_test is True
        assert cfg.infra_pulp is True


def test_config_no_file():
    config_data = config.ConfigFile.load()
    assert not config_data


def test_no_config_data():
    cfg = config.Config(config_data={})
    assert cfg.log_level_main == 'INFO'
    assert cfg.run_ansible_test is False
    assert cfg.infra_pulp is False
    assert cfg.infra_osd is False


def test_config_bad_ini_section(temp_config_file):
    with open(temp_config_file, 'w') as f:
        f.write('[bad-section]\nRUN_ANSIBLE_TEST = True')
        f.flush()
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        assert cfg.log_level_main == 'INFO'
        assert cfg.run_ansible_test is False
        assert cfg.infra_pulp is False
        assert cfg.infra_osd is False


def test_config_with_non_boolean(temp_config_file):
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nRUN_ANSIBLE_TEST = True\n'
                'LOG_LEVEL_MAIN = DEBUG')
        f.flush()
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        assert cfg.log_level_main == 'DEBUG'
        assert cfg.run_ansible_test is True
        assert cfg.infra_pulp is False
        assert cfg.infra_osd is False
