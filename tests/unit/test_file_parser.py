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
from galaxy_importer import file_parser


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

BAD_YAML = "my_key: : : : : '>=2.9.10,<2.11.5'"

TOO_LONG_REQUIRES_ANSIBLE = "requires_ansible: '>=" + "2" * 256 + "'"

BAD_VERSION_SPEC = "requires_ansible: '37'"

EXTENSIONS_GOOD = """
extensions:
  - args:
      ext_dir: eda/plugins/event_filters
  - args:
      ext_dir: eda/plugins/event_sources
  - args:
      ext_dir: custom/plugins/custom_type
"""

EXTENSIONS_MISSING_EXTENSIONS_KEY = """
wrong_key:
  - args:
      ext_dir: eda/plugins/event_filters
"""

EXTENSIONS_MISSING_ARGS_KEY = """
extensions:
  - wrong_key:
      ext_dir: eda/plugins/event_filters
  - args:
      ext_dir: eda/plugins/event_sources
"""

EXTENSIONS_MISSING_DIR_KEY = """
extensions:
  - args:
      ext_dir: eda/plugins/event_filters
  - args:
      wrong_key: eda/plugins/event_sources
"""


def test_no_runtime_file(tmpdir):
    parser = file_parser.RuntimeFileParser(collection_path=tmpdir)
    assert parser.data is None


def test_runtime_file_bad_yaml(tmpdir):
    tmpdir.mkdir("meta").join("runtime.yml").write(BAD_YAML)
    with pytest.raises(exc.FileParserError, match="Error during parsing of runtime.yml"):
        file_parser.RuntimeFileParser(collection_path=tmpdir)


def test_runtime_no_meta_runtime(tmpdir):
    parser = file_parser.RuntimeFileParser(collection_path=tmpdir)
    with pytest.raises(
        exc.FileParserError,
        match=r"'requires_ansible' in meta/runtime.yml is mandatory",
    ):
        parser.get_requires_ansible()


def test_no_requires_ansible(tmpdir):
    tmpdir.mkdir("meta").join("runtime.yml").write(RUNTIME_PLUGIN_ROUTING)
    parser = file_parser.RuntimeFileParser(collection_path=tmpdir)
    with pytest.raises(
        exc.FileParserError,
        match=r"'requires_ansible' in meta/runtime.yml is mandatory",
    ):
        parser.get_requires_ansible()


def test_get_requires_ansible(tmpdir):
    tmpdir.mkdir("meta").join("runtime.yml").write(RUNTIME_FULL_YAML)
    parser = file_parser.RuntimeFileParser(collection_path=tmpdir)
    requires_ansible = parser.get_requires_ansible()
    assert requires_ansible == ">=2.9.10,<2.11.5"


def test_too_long_requires_ansible(tmpdir):
    tmpdir.mkdir("meta").join("runtime.yml").write(TOO_LONG_REQUIRES_ANSIBLE)
    parser = file_parser.RuntimeFileParser(collection_path=tmpdir)
    with pytest.raises(
        exc.FileParserError,
        match="'requires_ansible' must not be greater than 255 characters",
    ):
        parser.get_requires_ansible()


def test_bad_version_spec(tmpdir):
    tmpdir.mkdir("meta").join("runtime.yml").write(BAD_VERSION_SPEC)
    parser = file_parser.RuntimeFileParser(collection_path=tmpdir)
    with pytest.raises(
        exc.FileParserError,
        match="not a valid requirement specification",
    ):
        parser.get_requires_ansible()


def test_extensions_file_bad_yaml(tmpdir):
    tmpdir.mkdir("meta").join("extensions.yml").write(BAD_YAML)
    with pytest.raises(exc.FileParserError, match="Error during parsing of extensions.yml"):
        file_parser.ExtensionsFileParser(collection_path=tmpdir)


def test_extensions_file_good_yaml(tmpdir):
    tmpdir.mkdir("meta").join("extensions.yml").write(EXTENSIONS_GOOD)
    parser = file_parser.ExtensionsFileParser(collection_path=tmpdir)
    assert parser.get_extension_dirs() == [
        "eda/plugins/event_filters",
        "eda/plugins/event_sources",
        "custom/plugins/custom_type",
    ]


@pytest.mark.parametrize(
    "extensions_yaml",
    [EXTENSIONS_MISSING_EXTENSIONS_KEY, EXTENSIONS_MISSING_ARGS_KEY, EXTENSIONS_MISSING_DIR_KEY],
)
def test_extensions_file_missing_keys(tmpdir, extensions_yaml):
    tmpdir.mkdir("meta").join("extensions.yml").write(extensions_yaml)
    parser = file_parser.ExtensionsFileParser(collection_path=tmpdir)
    with pytest.raises(
        exc.FileParserError, match="meta/extensions.yml is not in the expected format"
    ):
        parser.get_extension_dirs()


def test_no_extensions_file(tmpdir):
    # no error expected if meta/extensions.yml is not present
    parser = file_parser.ExtensionsFileParser(collection_path=tmpdir)
    parser.get_extension_dirs()
