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
import tempfile
import shutil
import json

from galaxy_importer import exceptions as exc
from galaxy_importer import file_parser
from galaxy_importer import constants
from galaxy_importer.schema import Content

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


class TestPatternsParser:

    def setup_method(self):
        self.collection_path = tempfile.mkdtemp()
        self.patterns_dir = os.path.join(self.collection_path, "extensions", "patterns")
        os.makedirs(self.patterns_dir, exist_ok=True)

    def teardown_method(self):
        shutil.rmtree(self.collection_path)

    def _create_pattern_dir(self, dir):
        pattern_dir = os.path.join(self.patterns_dir, dir)
        os.makedirs(pattern_dir, exist_ok=True)

        return pattern_dir

    def _create_meta_pattern_file(self, dir, content):
        pattern_dir = self._create_pattern_dir(dir)

        meta_dir = os.path.join(pattern_dir, "meta")
        os.makedirs(meta_dir, exist_ok=True)

        pattern_file_path = os.path.join(meta_dir, constants.META_PATTERN_FILENAME)

        with open(pattern_file_path, "w+") as file:
            json.dump(content, file)

        return content

    def _create_playbook(self, dir, filename, content="---"):
        pattern_dir = self._create_pattern_dir(dir)

        playbooks_dir = os.path.join(pattern_dir, "playbooks")
        os.makedirs(playbooks_dir, exist_ok=True)

        with open(os.path.join(playbooks_dir, filename), "w") as fh:
            fh.write(content)
            fh.flush()

        return content

    @pytest.mark.parametrize(
        "dirs", [[], ["foo.bar"], ["network.backup", "network.restore", "network.cleanup"]]
    )
    def test_loading_directories(self, dirs):
        for dir in dirs:
            self._create_pattern_dir(dir)

        patterns_parser = file_parser.PatternsParser(self.collection_path)
        patterns_parser._load()
        patterns_dirs = patterns_parser.get_dirs()

        assert set(dirs) == set(patterns_dirs)

    def test_load_meta_pattern_file(self):
        pattern_content = self._create_meta_pattern_file("foo.bar", {"foo": "bar"})

        patterns_parser = file_parser.PatternsParser(self.collection_path)
        loaded_pattern_content = patterns_parser._load_meta_pattern("foo.bar")
        assert loaded_pattern_content == pattern_content

    def test_loading_missing_meta_pattern_file(self):
        patterns_parser = file_parser.PatternsParser(self.collection_path)
        with pytest.raises(
            exc.FileParserError,
            match="Error during parsing of extensions/patterns/foo.bar/meta/pattern.json",
        ):
            patterns_parser._load_meta_pattern("foo.bar")

    @pytest.mark.parametrize(
        "dirs",
        [
            [],
            [
                {"name": "network.backup", "content": {"foo": "bar"}},
                {"name": "network.restore", "content": {"foo": "baz"}},
                {"name": "network.cleanup", "content": {"foo": "bax"}},
            ],
        ],
    )
    def test_get_meta_patterns(self, dirs):
        for dir in dirs:
            self._create_meta_pattern_file(dir["name"], content=dir["content"])

        patterns_parser = file_parser.PatternsParser(self.collection_path)
        meta_patterns_content = patterns_parser.get_meta_patterns()
        assert sorted(meta_patterns_content, key=lambda d: d["foo"]) == sorted(
            [dir["content"] for dir in dirs], key=lambda d: d["foo"]
        )

    def test_patterns_validate_playbooks_count(self):
        pattern = "foo.bar"
        contents = [
            Content(
                name=f"patterns.{pattern}.playbooks.playbook1",
                content_type=constants.ContentType.PATTERNS,
            ),
            Content(
                name=f"patterns.{pattern}.playbooks.playbook1",
                content_type=constants.ContentType.PATTERNS,
            ),
        ]
        self._create_meta_pattern_file(pattern, content={"foo": "bar"})

        self._create_playbook(pattern, "playbook1.yml")
        self._create_playbook(pattern, "playbook2.yml")

        patterns_parser = file_parser.PatternsParser(self.collection_path, contents=contents)
        pattern_content = patterns_parser._load_meta_pattern(pattern)
        with pytest.raises(
            exc.FileParserError, match="Multiple playbooks found, primary playbook must be defined"
        ):
            patterns_parser.validate_playbooks_count(pattern, pattern_content)
