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

from galaxy_importer import exceptions as exc
from galaxy_importer import loaders


RUNTIME_REQUIRES_ANSIBLE = "requires_ansible: '>=2.9.10,<2.11.5'"

RUNTIME_PLUGIN_ROUTING = """
plugin_routing:
  modules:
    set_config:
      redirect: my_ns.devops.devops_set_config
      deprecation:
        removal_date: '2022-06-01'
        warning_text: See the plugin documentation for more details
"""

RUNTIME_FULL_YAML = RUNTIME_REQUIRES_ANSIBLE + RUNTIME_PLUGIN_ROUTING

BAD_YAML = "requires_ansible: : : : : '>=2.9.10,<2.11.5'"

TOO_LONG_REQUIRES_ANSIBLE = "requires_ansible: '>=" + "2" * 256 + "'"

BAD_VERSION_SPEC = "requires_ansible: '>=2,<=3,,,'"


def test_no_runtime_file(tmpdir):
    loader = loaders.RuntimeFileLoader(collection_path=tmpdir)
    assert loader.data is None


def test_runtime_file_bad_yaml(tmpdir):
    tmpdir.mkdir("meta").join("runtime.yml").write(BAD_YAML)
    with pytest.raises(exc.RuntimeFileError, match="Error during parsing of runtime.yml"):
        loaders.RuntimeFileLoader(collection_path=tmpdir)


def test_runtime_no_meta_runtime(tmpdir):
    loader = loaders.RuntimeFileLoader(collection_path=tmpdir)
    with pytest.raises(
        exc.RuntimeFileError,
        match=r"'requires_ansible' in meta/runtime.yml is mandatory",
    ):
        loader.get_requires_ansible()


def test_no_requires_ansible(tmpdir):
    tmpdir.mkdir("meta").join("runtime.yml").write(RUNTIME_PLUGIN_ROUTING)
    loader = loaders.RuntimeFileLoader(collection_path=tmpdir)
    with pytest.raises(
        exc.RuntimeFileError,
        match=r"'requires_ansible' in meta/runtime.yml is mandatory",
    ):
        loader.get_requires_ansible()


def test_get_requires_ansible(tmpdir):
    tmpdir.mkdir("meta").join("runtime.yml").write(RUNTIME_FULL_YAML)
    loader = loaders.RuntimeFileLoader(collection_path=tmpdir)
    requires_ansible = loader.get_requires_ansible()
    assert requires_ansible == ">=2.9.10,<2.11.5"


def test_too_long_requires_ansible(tmpdir):
    tmpdir.mkdir("meta").join("runtime.yml").write(TOO_LONG_REQUIRES_ANSIBLE)
    with pytest.raises(
        exc.RuntimeFileError,
        match="'requires_ansible' must not be greater than 255 characters",
    ):
        loader = loaders.RuntimeFileLoader(collection_path=tmpdir)
        loader.get_requires_ansible()


def test_bad_version_spec(tmpdir):
    tmpdir.mkdir("meta").join("runtime.yml").write(BAD_VERSION_SPEC)
    with pytest.raises(
        exc.RuntimeFileError,
        match="not a valid semantic_version requirement specification",
    ):
        loader = loaders.RuntimeFileLoader(collection_path=tmpdir)
        loader.get_requires_ansible()
