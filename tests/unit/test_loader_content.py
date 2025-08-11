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

import json
import os
import shutil
import tempfile
from types import SimpleNamespace
from unittest import mock

import attr
import pytest

from galaxy_importer import constants
from galaxy_importer import exceptions as exc
from galaxy_importer import loaders
from galaxy_importer import schema

import logging

log = logging.getLogger(__name__)


ANSIBLE_DOC_OUTPUT = """
    {"module": {
        "my_ns.my_collection.my_module": {
            "doc": {
                "description": ["Sample module for testing."],
                "short_description": "Sample module for testing",
                "version_added": "2.8",
                "options": {
                    "exclude": {
                        "description": ["This is the message to send..."],
                        "required": "true"
                    },
                    "use_new": {
                        "description": ["Control is passed..."],
                        "version_added": "2.7",
                        "default": "auto"
                    }
                }
            },
            "examples": null,
            "metadata": null,
            "return": {
                "message": {
                    "description": "The output message the sample module generates"
                },
                "original_message": {
                    "description": "The original name param that was passed in",
                    "type": "str"
                }
            }
        },
        "my_ns.my_collection.subdir1.subdir2.my_module_2": {
            "doc": {
                "short_description": "Module with subdirs",
                "version_added": "2.9"
            }
        }
    }}
"""


@pytest.fixture
def loader_module():
    return loaders.PluginLoader(
        content_type=constants.ContentType.MODULE,
        rel_path="plugins/modules/my_module.py",
        root="/tmp_placeholder/tmp_placeholder/ansible_collections/my_ns/my_collection",
        cfg=SimpleNamespace(run_flake8=True),
        doc_strings=json.loads(ANSIBLE_DOC_OUTPUT),
    )


@pytest.fixture
def loader_exension():
    return loaders.ExtensionLoader(
        content_type=constants.ContentType.EDA_EVENT_SOURCE,
        rel_path="extensions/eda/plugins/event_sources/my_event_source.py",
        root="/tmp_placeholder/tmp_placeholder/ansible_collections/my_ns/my_collection",
        cfg=SimpleNamespace(run_flake8=True),
        doc_strings={},
    )


@pytest.fixture
def loader_doc_fragment():
    return loaders.PluginLoader(
        content_type=constants.ContentType.DOC_FRAGMENTS_PLUGIN,
        rel_path="plugins/doc_fragments/my_doc_fragment.py",
        root="/tmp_placeholder/tmp_placeholder/ansible_collections/my_ns/my_collection",
        cfg=SimpleNamespace(run_flake8=False),
        doc_strings=json.loads(ANSIBLE_DOC_OUTPUT),
    )


@pytest.fixture
def loader_role():
    return loaders.RoleLoader(
        content_type=constants.ContentType.ROLE,
        rel_path="roles/my_sample_role",
        cfg=SimpleNamespace(run_ansible_lint=True, ansible_local_tmp="~/.ansible/tmp"),
        root="/tmp_placeholder/tmp_placeholder/ansible_collections/my_ns/my_collection",
    )


@pytest.fixture
def loader_module_subdirs():
    return loaders.PluginLoader(
        content_type=constants.ContentType.MODULE,
        rel_path="plugins/modules/subdir1/subdir2/my_module_2.py",
        root="/tmp_placeholder/tmp_placeholder/ansible_collections/my_ns/my_collection",
        cfg=SimpleNamespace(run_flake8=False),
        doc_strings=json.loads(ANSIBLE_DOC_OUTPUT),
    )


@pytest.fixture
def loader_role_subdirs():
    return loaders.RoleLoader(
        content_type=constants.ContentType.ROLE,
        rel_path="roles/subdir1/subdir2/my_sample_role",
        root="/tmp_placeholder/tmp_placeholder/ansible_collections/my_ns/my_collection",
    )


def test_get_loader_cls():
    res = loaders.get_loader_cls(constants.ContentType.MODULE)
    assert issubclass(res, loaders.PluginLoader)
    assert not issubclass(res, loaders.RoleLoader)

    res = loaders.get_loader_cls(constants.ContentType.ROLE)
    assert issubclass(res, loaders.RoleLoader)
    assert not issubclass(res, loaders.PluginLoader)

    res = loaders.get_loader_cls(constants.ContentType.EDA_EVENT_SOURCE)
    assert issubclass(res, loaders.ExtensionLoader)

    res = loaders.get_loader_cls(constants.ContentType.PATTERNS)
    assert issubclass(res, loaders.PatternsLoader)
    assert issubclass(res, loaders.ContentLoader)


def test_init_plugin_loader(loader_module):
    assert loader_module.name == "my_module"
    assert loader_module.path_name == "my_module"


def test_init_extension_loader(loader_exension):
    assert loader_exension.name == "my_event_source"
    assert loader_exension.path_name == "my_event_source"


def test_init_role_loader(loader_role):
    assert loader_role.name == "my_sample_role"
    assert loader_role.path_name == "my_sample_role"


def test_init_plugin_loader_subdirs(loader_module_subdirs):
    assert loader_module_subdirs.name == "my_module_2"
    assert loader_module_subdirs.path_name == "subdir1.subdir2.my_module_2"


def test_init_role_loader_subdirs(loader_role_subdirs):
    assert loader_role_subdirs.name == "my_sample_role"
    assert loader_role_subdirs.path_name == "subdir1.subdir2.my_sample_role"


def test_bad_plugin_name():
    with pytest.raises(exc.ContentNameError):
        loaders.PluginLoader(
            content_type=constants.ContentType.MODULE,
            rel_path="plugins/modules/bad-name-dashes.py",
            root="",
        )


def test_bad_role_name():
    with pytest.raises(exc.ContentNameError):
        loaders.RoleLoader(
            content_type=constants.ContentType.ROLE,
            rel_path="roles/bad-name-dashes",
            root="",
        )


def test_get_fq_collection_name(loader_module):
    root = "/tmp_placeholder/tmp_placeholder/ansible_collections/my_ns/my_collection"
    assert loader_module._get_fq_collection_name(root) == "my_ns.my_collection"


def test_get_fq_name(loader_module):
    root = "/tmp_placeholder/tmp_placeholder/ansible_collections/my_ns/my_collection"
    res = loader_module._get_fq_name(root, "subdir.my_module")
    assert res == "my_ns.my_collection.subdir.my_module"


@mock.patch("galaxy_importer.loaders.content.Popen")
def test_plugin_loader_annotated_type(mocked_popen, loader_module):
    mocked_popen.return_value.stdout = ["my flake8 warning"]
    assert loader_module.name == "my_module"
    res = loader_module.load()
    assert isinstance(res, schema.Content)
    assert isinstance(res.content_type, attr.fields(schema.Content).content_type.type)


@mock.patch("galaxy_importer.loaders.content.Popen")
def test_load(mocked_popen, loader_module):
    mocked_popen.return_value.stdout = ""
    assert loader_module.name == "my_module"
    res = loader_module.load()
    assert isinstance(res, schema.Content)
    assert res.name == "my_module"
    assert res.content_type == constants.ContentType.MODULE
    assert res.description == "Sample module for testing"
    assert res.doc_strings["doc"]["version_added"] == "2.8"
    assert res.readme_file is None
    assert res.readme_html is None


def test_load_subdirs(loader_module_subdirs):
    assert loader_module_subdirs.name == "my_module_2"
    res = loader_module_subdirs.load()
    assert isinstance(res, schema.Content)
    assert res.name == "subdir1.subdir2.my_module_2"
    assert res.content_type == constants.ContentType.MODULE
    assert res.description == "Module with subdirs"
    assert res.doc_strings["doc"]["version_added"] == "2.9"
    assert res.readme_file is None
    assert res.readme_html is None


def test_load_doc_fragment_no_doc_strings(loader_doc_fragment):
    assert loader_doc_fragment.name == "my_doc_fragment"
    res = loader_doc_fragment.load()
    assert isinstance(res, schema.Content)
    assert res.name == "my_doc_fragment"
    assert res.content_type == constants.ContentType.DOC_FRAGMENTS_PLUGIN
    assert res.description is None
    assert res.doc_strings is None
    assert res.readme_file is None
    assert res.readme_html is None


@mock.patch("galaxy_importer.loaders.content.Popen")
def test_flake8_output(mocked_popen, loader_module):
    mocked_popen.return_value.stdout = ["my flake8 warning"]
    res = list(loader_module._run_flake8())
    assert res[0] == "my flake8 warning"


ROLE_METADATA = """---
galaxy_info:
  description: Test description inside metadata
  license: MIT
"""

ROLE_METADATA_MISSING_DESC = """---
galaxy_info:
  license: MIT
"""


@pytest.fixture
def temp_root():
    try:
        tmp = tempfile.mkdtemp()
        yield tmp
    finally:
        shutil.rmtree(tmp)


def test_find_metadata_file_path(temp_root, loader_role):
    root, rel_path = os.path.split(temp_root)

    res = loader_role._find_metadata_file_path(root, rel_path)
    assert res is None

    meta_dir = os.path.join(temp_root, "meta")
    os.mkdir(meta_dir)
    with open(os.path.join(meta_dir, "main.yml"), "w"):
        pass
    res = loader_role._find_metadata_file_path(root, rel_path)
    assert res == os.path.join(temp_root, "meta", "main.yml")


def test_get_role_metadata_desc(temp_root, loader_role):
    loader_role.rel_path = temp_root
    meta_dir = os.path.join(temp_root, "meta")
    os.mkdir(meta_dir)

    res = loader_role._get_metadata_description()
    assert res is None

    with open(os.path.join(meta_dir, "main.yml"), "w") as fp:
        fp.write(ROLE_METADATA)
    res = loader_role._get_metadata_description()
    assert res == "Test description inside metadata"

    with open(os.path.join(meta_dir, "main.yml"), "w") as fp:
        fp.write(ROLE_METADATA_MISSING_DESC)
    res = loader_role._get_metadata_description()
    assert res is None


def test_get_role_readme(temp_root, loader_role):
    loader_role.root = temp_root
    loader_role.rel_path = ""
    with open(os.path.join(temp_root, "README.md"), "w") as fp:
        fp.write("This is the role readme text")
    readme = loader_role._get_readme()
    assert readme.name == "README.md"
    assert readme.text == "This is the role readme text"


def test_get_role_readme_fail(temp_root, loader_role):
    loader_role.root = temp_root
    loader_role.rel_path = ""
    with pytest.raises(exc.ContentLoadError):
        loader_role._get_readme()


def test_load_role(temp_root, loader_role):
    loader_role.root = ""
    loader_role.rel_path = temp_root

    with open(os.path.join(temp_root, "README.md"), "w") as fp:
        fp.write("This is the role readme text")
    with open(os.path.join(temp_root, "meta.yml"), "w") as fp:
        fp.write(ROLE_METADATA)

    res = loader_role.load()
    assert isinstance(res, schema.Content)
    assert res.name == "my_sample_role"
    assert res.content_type == constants.ContentType.ROLE
    assert res.description == "Test description inside metadata"


@mock.patch("shutil.which")
def test_no_flake8_bin(mocked_shutil_which, loader_module, caplog):
    mocked_shutil_which.return_value = False
    assert loader_module.name == "my_module"
    loader_module.load()
    assert "flake8 not found, skipping" in [r.message for r in caplog.records]


class TestPatternsLoader:
    def setup_method(self):
        self.collection_path = tempfile.mkdtemp()
        self.patterns_dir = os.path.join(self.collection_path, "extensions", "patterns")
        os.makedirs(self.patterns_dir, exist_ok=True)

    def _create_pattern_dir(self, dir):
        pattern_dir = os.path.join(self.patterns_dir, dir)
        os.makedirs(pattern_dir, exist_ok=True)

        return pattern_dir

    def _create_path(self, *path, filename=None, content=None):
        dir_file_path = self._create_pattern_dir(os.path.join(*path))

        path_to_file = os.path.join(dir_file_path, filename)

        with open(path_to_file, "w") as f:
            extension = filename.split(".")[1]
            if extension == "json":
                json.dump(content, f)
            else:
                f.write(content)
                f.flush()

        return os.path.relpath(path_to_file, self.collection_path)

    def _pattern_loader_content_type(self, path, content_type=None):
        return loaders.PatternsLoader(
            content_type=content_type,
            rel_path=path,
            root=self.collection_path,
            cfg=SimpleNamespace(run_flake8=True, offline_ansible_lint=False),
            doc_strings={},
        )

    def teardown_method(self):
        shutil.rmtree(self.collection_path)

    def test_load_all_content_types(self):
        content_types_with_paths = [
            (
                constants.ContentType.PATTERNS,
                self._create_path(
                    "network.backup", "meta", filename="pattern.json", content={"foo": "bar"}
                ),
            ),
            (
                constants.ContentType.PATTERNS,
                self._create_path(
                    "network.backup", "playbooks", filename="playbook.yml", content="---"
                ),
            ),
            (
                constants.ContentType.PATTERNS,
                self._create_path(
                    "network.backup", "templates", filename="rhdh.yml", content="---"
                ),
            ),
        ]

        for content_type, path in content_types_with_paths:
            pattern_loader = self._pattern_loader_content_type(path, content_type)
            content = pattern_loader.load()

            assert content_type == content.content_type
            assert content.name == path.replace("/", ".").replace("extensions.", "")
