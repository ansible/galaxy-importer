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

import os

import pytest
from pytest_mock import mocker  # noqa F401

from galaxy_importer import config
from galaxy_importer.ansible_test import runner


@pytest.fixture
def temp_config_file():
    try:
        dir = os.path.dirname(os.path.dirname(__file__))
        config_file = os.path.join(dir, 'galaxy_importer', 'galaxy-importer.cfg')
        yield config_file
    finally:
        os.remove(config_file)


def test_no_config_file():
    cfg = config.Config()
    cfg._load_config()
    assert cfg.log_debug_main is False
    assert cfg.run_ansible_test is False
    assert cfg.infra_pulp is False
    assert cfg.infra_osd is False


def test_config_set_from_file(temp_config_file):
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nRUN_ANSIBLE_TEST = True\n'
                'INFRA_PULP = True')
        f.flush()
        cfg = config.Config()
        cfg._load_config()
        assert cfg.log_debug_main is False
        assert cfg.run_ansible_test is True
        assert cfg.infra_pulp is True
        assert cfg.infra_osd is False


def test_config_bad_ini_section(temp_config_file):
    with open(temp_config_file, 'w') as f:
        f.write('[bad-section]\nRUN_ANSIBLE_TEST = True')
        f.flush()
        cfg = config.Config()
        cfg._load_config()
        assert cfg.log_debug_main is False
        assert cfg.run_ansible_test is False
        assert cfg.infra_pulp is False
        assert cfg.infra_osd is False


def test_runner_no_config_file(mocker):  # noqa F811
    config.Config()._load_config()
    ansible_test_runner = runner.AnsibleTestRunner()
    mocker.patch.object(ansible_test_runner, '_run_ansible_test_local')
    ansible_test_runner.run()
    assert not ansible_test_runner._run_ansible_test_local.called


def test_runner_ansible_test_local(mocker, temp_config_file):  # noqa F811
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nRUN_ANSIBLE_TEST = True')
        f.flush()
        config.Config()._load_config()

        ansible_test_runner = runner.AnsibleTestRunner()
        mocker.patch.object(ansible_test_runner, '_run_ansible_test_local')
        ansible_test_runner.run()
        assert ansible_test_runner._run_ansible_test_local.called


def test_runner_pulp(mocker, temp_config_file):  # noqa F811
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nRUN_ANSIBLE_TEST = True\n'
                'INFRA_PULP = True')
        f.flush()
        config.Config()._load_config()

        ansible_test_runner = runner.AnsibleTestRunner()
        mocker.patch.object(ansible_test_runner, '_run_image_local')
        ansible_test_runner.run()
        assert ansible_test_runner._run_image_local.called


def test_runner_pulp_and_osd(mocker, temp_config_file):  # noqa F811
    with open(temp_config_file, 'w') as f:
        f.write('[galaxy-importer]\nRUN_ANSIBLE_TEST = True\n'
                'INFRA_PULP = True\nINFRA_OSD = True')
        f.flush()
        config.Config()._load_config()

        ansible_test_runner = runner.AnsibleTestRunner()
        mocker.patch.object(ansible_test_runner, '_run_image_openshift_job')
        ansible_test_runner.run()
        assert ansible_test_runner._run_image_openshift_job.called
