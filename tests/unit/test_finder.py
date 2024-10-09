# (c) 2012-2023, Ansible by Red Hat
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
import shutil
import tempfile
import unittest

import pytest

from galaxy_importer.finder import ContentFinder, FileWalker

log = logging.getLogger(__name__)


EXTENSIONS_META = """
extensions:
  - args:
      ext_dir: eda/plugins/event_filter
  - args:
      ext_dir: eda/plugins/event_source
  - args:
      ext_dir: custom/plugins/custom_type
"""


class TestContentFinder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.temp_dir, "ansible_collections", "foo", "bar")
        os.makedirs(self.base_dir)

        os.mkdir(os.path.join(self.base_dir, "plugins"))
        self.module_dir = os.path.join(self.base_dir, "plugins", "modules")
        os.mkdir(self.module_dir)

        self.roles_dir = os.path.join(self.base_dir, "roles")
        os.mkdir(self.roles_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @pytest.fixture(autouse=True)
    def inject_caplog(self, caplog):
        self._caplog = caplog

    def test_find_content(self):

        with open(os.path.join(self.module_dir, "__init__.py"), "w"):
            pass
        with open(os.path.join(self.module_dir, "first_module.py"), "w"):
            pass
        with open(os.path.join(self.module_dir, "second_module.py"), "w"):
            pass

        my_roles_dir = os.path.join(self.roles_dir, "my_role")
        os.mkdir(my_roles_dir)
        os.mkdir(os.path.join(my_roles_dir, "tasks"))

        contents = ContentFinder().find_contents(self.base_dir)

        content_items = [os.path.basename(c.path) for c in contents]
        assert "first_module.py" in content_items
        assert "second_module.py" in content_items
        assert "__init__.py" not in content_items
        assert "my_role" in content_items
        assert len(content_items) == 3

    def test_find_no_content(self):
        contents = ContentFinder().find_contents(self.base_dir)
        assert not any(True for _ in contents)

    @pytest.mark.skip(reason="don't care anymore?")
    def test_skip_plugin_files(self):
        with open(os.path.join(self.module_dir, "__init__.py"), "w"):
            pass
        with open(os.path.join(self.module_dir, "main.go"), "w"):
            pass
        contents = ContentFinder().find_contents(self.base_dir)
        assert not any(True for _ in contents)

    def test_nested_plugin(self):
        subdir1 = os.path.join(self.module_dir, "subdir1")
        os.mkdir(subdir1)
        subdir2 = os.path.join(subdir1, "subdir2")
        os.mkdir(subdir2)
        with open(os.path.join(subdir2, "nested_module.py"), "w"):
            pass

        contents = ContentFinder().find_contents(self.base_dir)
        assert list(contents)[0].path == "plugins/modules/subdir1/subdir2/nested_module.py"

    def test_nested_role(self):
        subdir1 = os.path.join(self.roles_dir, "subdir1")
        os.mkdir(subdir1)
        role_dir = os.path.join(subdir1, "my_role")
        os.mkdir(role_dir)

        contents = ContentFinder().find_contents(self.base_dir)
        assert len(contents) == 0

        dir_in_role = os.path.join(role_dir, "tasks")
        os.mkdir(dir_in_role)

        contents = ContentFinder().find_contents(self.base_dir)
        assert list(contents)[0].path == "roles/subdir1/my_role"

    def test_error_file_in_roles_dir(self):
        with open(os.path.join(self.roles_dir, "main.yml"), "w"):
            pass
        my_roles_dir = os.path.join(self.roles_dir, "my_role")
        os.mkdir(my_roles_dir)
        os.mkdir(os.path.join(my_roles_dir, "tasks"))

        contents = ContentFinder().find_contents(self.base_dir)
        content_items = [os.path.basename(c.path) for c in contents]
        assert "my_role" in content_items
        assert len(content_items) == 1

    def test_extensions_metadata_and_path_exist(self):
        event_sources_path = os.path.join(self.base_dir, "extensions/eda/plugins/event_source")
        os.makedirs(event_sources_path, exist_ok=True)
        with open(os.path.join(event_sources_path, "my_event_source.py"), "w"):
            pass

        ext_metadata_path = os.path.join(self.base_dir, "meta")
        os.mkdir(ext_metadata_path)
        with open(os.path.join(ext_metadata_path, "extensions.yml"), "w") as f:
            f.write(EXTENSIONS_META)

        self._caplog.set_level(logging.INFO)

        contents = list(ContentFinder().find_contents(self.base_dir))
        assert len(contents) == 1
        assert contents[0].content_type.value == "eda/plugins/event_source"
        assert contents[0].path == "extensions/eda/plugins/event_source/my_event_source.py"

        custom_ext_log = (
            "The extension type 'custom/plugins/custom_type' listed in 'meta/extensions.yml' "
            "is custom and will not be listed in Galaxy's contents nor documentation"
        )

        assert custom_ext_log in [r.message for r in self._caplog.records]

    def test_extensions_metadata_exists_path_not(self):
        ext_metadata_path = os.path.join(self.base_dir, "meta")
        os.mkdir(ext_metadata_path)
        with open(os.path.join(ext_metadata_path, "extensions.yml"), "w") as f:
            f.write(EXTENSIONS_META)

        contents = list(ContentFinder().find_contents(self.base_dir))
        assert len(contents) == 0

    def test_extensions_path_exists_metadata_not(self):
        event_sources_path = os.path.join(self.base_dir, "extensions/eda/plugins/event_source")
        os.makedirs(event_sources_path, exist_ok=True)
        with open(os.path.join(event_sources_path, "my_event_source.py"), "w"):
            pass

        contents = list(ContentFinder().find_contents(self.base_dir))
        assert len(contents) == 0


@pytest.fixture
def walker_dir(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "hello.txt"
    p.write_text("blippy")
    d2 = d / "another_level"
    d2.mkdir()
    f = d2 / "example.txt"
    f.write_text("an example")
    return tmp_path


def test_file_walker(walker_dir):
    file_walker = FileWalker(walker_dir)
    file_name_generator = file_walker.walk()
    for file_name in file_name_generator:
        log.debug("file_name: %s", file_name)
        assert os.path.exists(file_name)
