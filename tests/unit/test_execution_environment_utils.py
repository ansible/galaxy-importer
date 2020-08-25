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

from galaxy_importer.utils import execution_environment as ee_utils


logger = logging.getLogger(__name__)


EE_YAML = """---
version: 1
dependencies:
  galaxy: requirements.yml
  python: requirements.txt
  system: bindep.txt

additional_build_steps:
  prepend: |
    RUN whoami
    RUN cat /etc/os-release
  append:
    - RUN echo This is a post-install command!
    - RUN ls -la /etc
"""


EE_DIR_YAML = """---
version: 1
dependencies:
  galaxy: meta/requirements.yml
  python: meta/requirements.txt
  system: meta/bindep.txt

additional_build_steps:
  prepend: |
    RUN whoami
    RUN cat /etc/os-release
  append:
    - RUN echo This is a post-install command!
    - RUN ls -la /etc
"""

REQUIREMENTS_YML = """
---
collections:
  - name: https://github.com/AlanCoding/awx.git#awx_collection,ee_req
    type: git
  - name: https://github.com/AlanCoding/azure.git
    version: ee_req
    type: git
"""


IMPORTED_REQUIREMENTS_YML = {
    'collections': [
        {
            'name': 'https://github.com/AlanCoding/awx.git#awx_collection,ee_req',
            'type': 'git'
        },
        {
            'name': 'https://github.com/AlanCoding/azure.git',
            'version': 'ee_req',
            'type': 'git'
        },
    ]
}


REQUIREMENTS_TXT = """
ansible
paramiko
"""

BINDEP_TXT = """
gcc
python3-devel
libcurl-devel
openssl-devel
libxml2-devel
"""


WRITE_TO_EE_RESULT = {
    'dependencies': {
        'galaxy': {
            'collections': [
                {
                    'name': 'https://github.com/AlanCoding/awx.git#awx_collection,ee_req',
                    'type': 'git'
                },
                {
                    'name': 'https://github.com/AlanCoding/azure.git',
                    'version': 'ee_req',
                    'type': 'git'
                },
            ]
        }
    }
}


PROCESSED_EE = {
    'version': 1,
    'dependencies': {
        'galaxy': {
            'collections': [
                {
                    'name': 'https://github.com/AlanCoding/awx.git#awx_collection,ee_req',
                    'type': 'git'
                },
                {
                    'name': 'https://github.com/AlanCoding/azure.git',
                    'version': 'ee_req',
                    'type': 'git'
                },
            ]
        },
        'python': [
            'ansible: []',
            'paramiko: []'
        ],
        'system': [
            'gcc',
            'python3-devel',
            'libcurl-devel',
            'openssl-devel',
            'libxml2-devel'
        ]

    },
    'additional_build_steps': {
        'prepend': 'RUN whoami\nRUN cat /etc/os-release\n',
        'append': [
            'RUN echo This is a post-install command!',
            'RUN ls -la /etc'
        ]
    }
}


@pytest.fixture
def tmp_yml_file():
    try:
        dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        tmp_file = os.path.join(dir, 'requirements.yml')
        yield tmp_file
    finally:
        os.remove(tmp_file)


@pytest.fixture
def tmp_txt_file():
    try:
        dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        tmp_file = os.path.join(dir, 'file.txt')
        yield tmp_file
    finally:
        os.remove(tmp_file)


def test_process_execution_environment():
    dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.mkdir(os.path.join(dir, 'meta'))
    files = [
        os.path.join(dir, 'meta/execution-environment.yml'),
        os.path.join(dir, 'requirements.yml'),
        os.path.join(dir, 'requirements.txt'),
        os.path.join(dir, 'bindep.txt')
    ]
    file_contents = [EE_YAML, REQUIREMENTS_YML, REQUIREMENTS_TXT, BINDEP_TXT]
    try:
        for f, c in zip(files, file_contents):
            with open(f, 'w') as fp:
                fp.write(c)
                fp.flush()
        res = ee_utils.process_execution_environment(dir, logger)
        assert res == PROCESSED_EE
    finally:
        for f in files:
            os.remove(f)
        os.rmdir(os.path.join(dir, 'meta'))


def test_process_execution_environment_deps_in_directory():
    dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.mkdir(os.path.join(dir, 'meta'))
    files = [
        os.path.join(dir, 'meta/execution-environment.yml'),
        os.path.join(dir, 'meta/requirements.yml'),
        os.path.join(dir, 'meta/requirements.txt'),
        os.path.join(dir, 'meta/bindep.txt')
    ]
    file_contents = [EE_DIR_YAML, REQUIREMENTS_YML, REQUIREMENTS_TXT, BINDEP_TXT]
    try:
        for f, c in zip(files, file_contents):
            with open(f, 'w') as fp:
                fp.write(c)
                fp.flush()
        res = ee_utils.process_execution_environment(dir, logger)
        assert res == PROCESSED_EE
    finally:
        for f in files:
            os.remove(f)
        os.rmdir(os.path.join(dir, 'meta'))


def test_process_execution_environment_no_files():
    path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    res = ee_utils.process_execution_environment(path, logger)
    assert res == {}


def test_load_list(tmp_txt_file):
    with open(tmp_txt_file, 'w') as f:
        f.write(BINDEP_TXT)
        f.flush()
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'file.txt'
        )
        res = ee_utils._load_list(path)
        assert res == [
            'gcc',
            'python3-devel',
            'libcurl-devel',
            'openssl-devel',
            'libxml2-devel'
        ]
    pass


def test_load_python(tmp_txt_file):
    with open(tmp_txt_file, 'w') as f:
        f.write(REQUIREMENTS_TXT)
        f.flush()
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'file.txt'
        )
        res = ee_utils._load_python(path)
        assert res == [
            'ansible: []',
            'paramiko: []'
        ]


def test_load_yaml(tmp_yml_file):
    with open(tmp_yml_file, 'w') as f:
        f.write(REQUIREMENTS_YML)
        f.flush()
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'requirements.yml'
        )
        res = ee_utils._load_yaml(path, logger)
        assert res == IMPORTED_REQUIREMENTS_YML


def test_write_to_ee():
    ee = {
        'dependencies': {}
    }
    key_name = 'galaxy'
    key_value = IMPORTED_REQUIREMENTS_YML
    res = ee_utils._write_to_ee(ee, key_name, key_value)
    assert res == WRITE_TO_EE_RESULT


def test_write_to_ee_no_dep_key():
    ee = {}
    key_name = 'galaxy'
    key_value = IMPORTED_REQUIREMENTS_YML
    res = ee_utils._write_to_ee(ee, key_name, key_value)
    assert res == WRITE_TO_EE_RESULT