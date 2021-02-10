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

from galaxy_importer.utils import execution_environment as ee_utils


logger = logging.getLogger(__name__)
EE_YAML = """
version: 1
dependencies:
  python: requirements.txt
  system: bindep.txt
"""
EE_ONLY_PYTHON_YAML = """
version: 1
dependencies:
  python: requirements.txt
"""
EE_ONLY_SYSTEM_YAML = """
version: 1
dependencies:
  system: bindep.txt
"""
REQUIREMENTS_TXT = """
google-auth>=1.0.1  # Apache-2.0
requests # Apache-2.0
requests-oauthlib # ISC
"""
BINDEP_TXT = """
# This is a cross-platform list tracking distribution packages needed by tests;
# see https://docs.openstack.org/infra/bindep/ for additional information.

libffi-devel [platform:rpm]
python3-devel [compile test platform:rpm]
"""


def test_process_execution_environment():
    dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.mkdir(os.path.join(dir, 'meta'))
    files = [
        os.path.join(dir, 'meta/execution-environment.yml'),
        os.path.join(dir, 'requirements.txt'),
        os.path.join(dir, 'bindep.txt')
    ]
    file_contents = [EE_YAML, REQUIREMENTS_TXT, BINDEP_TXT]
    try:
        for f, c in zip(files, file_contents):
            with open(f, 'w') as fp:
                fp.write(c)
                fp.flush()
        res = ee_utils.process_execution_environment(dir, logger)
        assert res == {
            'dependencies': {
                'python': [
                    'google-auth>=1.0.1  # Apache-2.0',
                    'requests # Apache-2.0',
                    'requests-oauthlib # ISC',
                ],
                'system': [
                    'libffi-devel [platform:rpm]',
                    'python3-devel [compile test platform:rpm]'
                ]
            }
        }
    finally:
        for f in files:
            os.remove(f)
        os.rmdir(os.path.join(dir, 'meta'))


def test_process_empty_execution_environment_with_local_files():
    dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.mkdir(os.path.join(dir, 'meta'))
    files = [
        os.path.join(dir, 'meta/execution-environment.yml'),
        os.path.join(dir, 'requirements.txt'),
        os.path.join(dir, 'bindep.txt')
    ]
    file_contents = ['version: 1', REQUIREMENTS_TXT, BINDEP_TXT]
    try:
        for f, c in zip(files, file_contents):
            with open(f, 'w') as fp:
                fp.write(c)
                fp.flush()
        res = ee_utils.process_execution_environment(dir, logger)
        assert res is None
    finally:
        for f in files:
            os.remove(f)
        os.rmdir(os.path.join(dir, 'meta'))


def test_process_python_execution_environment_with_local_system_file():
    dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.mkdir(os.path.join(dir, 'meta'))
    files = [
        os.path.join(dir, 'meta/execution-environment.yml'),
        os.path.join(dir, 'requirements.txt'),
        os.path.join(dir, 'bindep.txt')
    ]
    file_contents = [EE_ONLY_PYTHON_YAML, REQUIREMENTS_TXT, BINDEP_TXT]
    try:
        for f, c in zip(files, file_contents):
            with open(f, 'w') as fp:
                fp.write(c)
                fp.flush()
        res = ee_utils.process_execution_environment(dir, logger)
        assert res == {
            'dependencies': {
                'python': [
                    'google-auth>=1.0.1  # Apache-2.0',
                    'requests # Apache-2.0',
                    'requests-oauthlib # ISC',
                ]
            }
        }
    finally:
        for f in files:
            os.remove(f)
        os.rmdir(os.path.join(dir, 'meta'))


def test_process_system_execution_environment_with_local_python_file():
    dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.mkdir(os.path.join(dir, 'meta'))
    files = [
        os.path.join(dir, 'meta/execution-environment.yml'),
        os.path.join(dir, 'requirements.txt'),
        os.path.join(dir, 'bindep.txt')
    ]
    file_contents = [EE_ONLY_SYSTEM_YAML, REQUIREMENTS_TXT, BINDEP_TXT]
    try:
        for f, c in zip(files, file_contents):
            with open(f, 'w') as fp:
                fp.write(c)
                fp.flush()
        res = ee_utils.process_execution_environment(dir, logger)
        assert res == {
            'dependencies': {
                'system': [
                    'libffi-devel [platform:rpm]',
                    'python3-devel [compile test platform:rpm]'
                ]
            }
        }
    finally:
        for f in files:
            os.remove(f)
        os.rmdir(os.path.join(dir, 'meta'))


def test_process_execution_environment_no_python():
    EE_YAML = """
version: 1
dependencies:
  system: bindep.txt
"""
    dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.mkdir(os.path.join(dir, 'meta'))
    files = [
        os.path.join(dir, 'meta/execution-environment.yml'),
        os.path.join(dir, 'bindep.txt')
    ]
    file_contents = [EE_YAML, BINDEP_TXT]
    try:
        for f, c in zip(files, file_contents):
            with open(f, 'w') as fp:
                fp.write(c)
                fp.flush()
        res = ee_utils.process_execution_environment(dir, logger)
        assert res == {
            'dependencies': {
                'system': [
                    'libffi-devel [platform:rpm]',
                    'python3-devel [compile test platform:rpm]'
                ]
            }
        }
    finally:
        for f in files:
            os.remove(f)
        os.rmdir(os.path.join(dir, 'meta'))


def test_process_execution_environment_no_system():
    EE_YAML = """
version: 1
dependencies:
  python: requirements.txt
"""
    dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.mkdir(os.path.join(dir, 'meta'))
    files = [
        os.path.join(dir, 'meta/execution-environment.yml'),
        os.path.join(dir, 'requirements.txt')
    ]
    file_contents = [EE_YAML, REQUIREMENTS_TXT]
    try:
        for f, c in zip(files, file_contents):
            with open(f, 'w') as fp:
                fp.write(c)
                fp.flush()
        res = ee_utils.process_execution_environment(dir, logger)
        assert res == {
            'dependencies': {
                'python': [
                    'google-auth>=1.0.1  # Apache-2.0',
                    'requests # Apache-2.0',
                    'requests-oauthlib # ISC',
                ]
            }
        }
    finally:
        for f in files:
            os.remove(f)
        os.rmdir(os.path.join(dir, 'meta'))


def test_process_execution_environment_no_deps(caplog):
    EE_YAML = """
version: 1
"""
    dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.mkdir(os.path.join(dir, 'meta'))
    ee_file = os.path.join(dir, 'meta/execution-environment.yml')
    try:
        with open(ee_file, 'w') as fp:
            fp.write(EE_YAML)
            fp.flush()
        res = ee_utils.process_execution_environment(dir, logger)
        assert res is None
    finally:
        os.remove(ee_file)
        os.rmdir(os.path.join(dir, 'meta'))


DEPS = (['python1', 'python2', 'python3'], ['system1', 'system2', 'system3'])


def test_write_to_ee():
    ee = {
        'dependencies': {}
    }
    res = ee_utils._write_to_ee(ee, 'system', DEPS[1])
    assert res == {
        'dependencies': {
            'system': ['system1', 'system2', 'system3']
        }
    }


def test_write_to_ee_no_dep_key():
    res = ee_utils._write_to_ee({}, 'python', DEPS[0])
    assert res == {
        'dependencies': {
            'python': ['python1', 'python2', 'python3']
        }
    }
