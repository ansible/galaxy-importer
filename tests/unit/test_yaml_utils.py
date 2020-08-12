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

from galaxy_importer.utils import yaml as yaml_utils


@pytest.fixture
def tmp_file():
    try:
        dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        tmp_file = os.path.join(dir, 'env.yml')
        yield tmp_file
    finally:
        os.remove(tmp_file)


EX_ENV_YAML = """version: 1
dependencies:
  python:
    - somepkg==1.3
    - otherpkg>=3.0
  files:
    - "/usr/bin/oc"
    - "/usr/lib/libssl.so.1"
  system:
    - python3.6-dateutil
"""


def test_safe_load_file(tmp_file):
    data = {
        "version": 1,
        "dependencies": {
            "python": [
                "somepkg==1.3",
                "otherpkg>=3.0"
            ],
            "files": [
                "/usr/bin/oc",
                "/usr/lib/libssl.so.1"
            ],
            "system": [
                "python3.6-dateutil"
            ]
        }
    }
    with open(tmp_file, 'w') as f:
        f.write(EX_ENV_YAML)
        f.flush()
        res = yaml_utils.safe_load_file(tmp_file)
        assert res == data


def test_lint_file(tmp_file):
    with open(tmp_file, 'w') as f:
        f.write(EX_ENV_YAML)
        f.flush()
        res = list(yaml_utils.lint_file(tmp_file))
        assert len(res) == 1
