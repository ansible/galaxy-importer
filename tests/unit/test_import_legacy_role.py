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
import tempfile
import subprocess

import pytest

from galaxy_importer import legacy_role
from galaxy_importer.exceptions import ImporterError


def test_import_legacy_role_without_checkout(caplog):
    with pytest.raises(ImporterError):
        legacy_role.import_legacy_role(git_clone_path=None, logger=None)


def test_import_legacy_role_default_config(caplog):
    url = "https://github.com/geerlingguy/ansible-role-docker"

    with tempfile.TemporaryDirectory() as tmp_role_root:
        dn = os.path.join(tmp_role_root, "geerlingguy")
        os.makedirs(dn)
        dst = os.path.join(tmp_role_root, "geerlingguy", "docker")
        subprocess.run(f"git clone {url} {dst}", shell=True, check=True)
        metadata = legacy_role.import_legacy_role(git_clone_path=dst, logger=None)

    assert "WARNING" in caplog.text
    assert sorted(list(metadata.keys())) == [
        "content_type",
        "dependencies",
        "description",
        "license",
        "min_ansible_version",
        "name",
        "readme_file",
        "readme_html",
        "tags",
    ]


def test_import_legacy_role_with_config_no_lint(caplog):
    url = "https://github.com/geerlingguy/ansible-role-docker"

    class cfg:
        run_ansible_lint = False

    with tempfile.TemporaryDirectory() as tmp_role_root:
        dn = os.path.join(tmp_role_root, "geerlingguy")
        os.makedirs(dn)
        dst = os.path.join(tmp_role_root, "geerlingguy", "docker")
        subprocess.run(f"git clone {url} {dst}", shell=True, check=True)
        metadata = legacy_role.import_legacy_role(git_clone_path=dst, cfg=cfg(), logger=None)

    assert "WARNING" not in caplog.text
    assert sorted(list(metadata.keys())) == [
        "content_type",
        "dependencies",
        "description",
        "license",
        "min_ansible_version",
        "name",
        "readme_file",
        "readme_html",
        "tags",
    ]
