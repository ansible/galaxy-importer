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
import yaml

import pytest

from galaxy_importer.finder import ContentFinder, PatternsFinder, FileWalker
from galaxy_importer import constants
from galaxy_importer.exceptions import ContentFindError

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

        os.mkdir(os.path.join(self.temp_dir, "plugins"))
        self.module_dir = os.path.join(self.temp_dir, "plugins", "modules")
        os.mkdir(self.module_dir)

        self.roles_dir = os.path.join(self.temp_dir, "roles")
        os.mkdir(self.roles_dir)

        self.playbooks_dir = os.path.join(self.temp_dir, "playbooks")
        os.mkdir(self.playbooks_dir)

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

        contents = ContentFinder().find_contents(self.temp_dir)

        content_items = [os.path.basename(c.path) for c in contents]
        assert "first_module.py" in content_items
        assert "second_module.py" in content_items
        assert "__init__.py" not in content_items
        assert "my_role" in content_items
        assert len(content_items) == 3

    def test_find_no_content(self):
        contents = ContentFinder().find_contents(self.temp_dir)
        assert not any(True for _ in contents)

    def test_skip_plugin_files(self):
        with open(os.path.join(self.module_dir, "__init__.py"), "w"):
            pass
        with open(os.path.join(self.module_dir, "main.go"), "w"):
            pass
        contents = ContentFinder().find_contents(self.temp_dir)
        assert not any(True for _ in contents)

    def test_nested_plugin(self):
        subdir1 = os.path.join(self.module_dir, "subdir1")
        os.mkdir(subdir1)
        subdir2 = os.path.join(subdir1, "subdir2")
        os.mkdir(subdir2)
        with open(os.path.join(subdir2, "nested_module.py"), "w"):
            pass

        contents = ContentFinder().find_contents(self.temp_dir)
        assert next(iter(contents)).path == "plugins/modules/subdir1/subdir2/nested_module.py"

    def test_nested_role(self):
        subdir1 = os.path.join(self.roles_dir, "subdir1")
        os.mkdir(subdir1)
        role_dir = os.path.join(subdir1, "my_role")
        os.mkdir(role_dir)

        contents = ContentFinder().find_contents(self.temp_dir)
        assert len(contents) == 0

        dir_in_role = os.path.join(role_dir, "tasks")
        os.mkdir(dir_in_role)

        contents = ContentFinder().find_contents(self.temp_dir)
        assert next(iter(contents)).path == "roles/subdir1/my_role"

    def test_error_file_in_roles_dir(self):
        with open(os.path.join(self.roles_dir, "main.yml"), "w"):
            pass
        my_roles_dir = os.path.join(self.roles_dir, "my_role")
        os.mkdir(my_roles_dir)
        os.mkdir(os.path.join(my_roles_dir, "tasks"))

        contents = ContentFinder().find_contents(self.temp_dir)
        content_items = [os.path.basename(c.path) for c in contents]
        assert "my_role" in content_items
        assert len(content_items) == 1

    def test_extensions_metadata_and_path_exist(self):
        event_sources_path = os.path.join(self.temp_dir, "extensions/eda/plugins/event_source")
        os.makedirs(event_sources_path, exist_ok=True)
        with open(os.path.join(event_sources_path, "my_event_source.py"), "w"):
            pass

        ext_metadata_path = os.path.join(self.temp_dir, "meta")
        os.mkdir(ext_metadata_path)
        with open(os.path.join(ext_metadata_path, "extensions.yml"), "w") as f:
            f.write(EXTENSIONS_META)

        self._caplog.set_level(logging.INFO)

        contents = list(ContentFinder().find_contents(self.temp_dir))
        assert len(contents) == 1
        assert contents[0].content_type.value == "eda/plugins/event_source"
        assert contents[0].path == "extensions/eda/plugins/event_source/my_event_source.py"

        custom_ext_log = (
            "The extension type 'custom/plugins/custom_type' listed in 'meta/extensions.yml' "
            "is custom and will not be listed in Galaxy's contents nor documentation"
        )

        assert custom_ext_log in [r.message for r in self._caplog.records]

    def test_extensions_metadata_exists_path_not(self):
        ext_metadata_path = os.path.join(self.temp_dir, "meta")
        os.mkdir(ext_metadata_path)
        with open(os.path.join(ext_metadata_path, "extensions.yml"), "w") as f:
            f.write(EXTENSIONS_META)

        contents = list(ContentFinder().find_contents(self.temp_dir))
        assert len(contents) == 0

    def test_extensions_path_exists_metadata_not(self):
        event_sources_path = os.path.join(self.temp_dir, "extensions/eda/plugins/event_source")
        os.makedirs(event_sources_path, exist_ok=True)
        with open(os.path.join(event_sources_path, "my_event_source.py"), "w"):
            pass

        contents = list(ContentFinder().find_contents(self.temp_dir))
        assert len(contents) == 0

    def test_find_playbooks(self):

        content = [
            {
                "name": "a test playbook",
                "tasks": [
                    {
                        "name": "a task",
                        "shell": "whoami",
                    }
                ],
            }
        ]

        pb_path = os.path.join(self.playbooks_dir, "play1.yml")
        with open(pb_path, "w") as f:
            f.write(yaml.dump(content))

        contents = list(ContentFinder().find_contents(self.temp_dir))
        assert len(contents) == 1
        assert contents[0].content_type.name == "PLAYBOOK"
        assert contents[0].path == "playbooks/play1.yml"

    def test_find_powershell_modules(self):
        ps_fn = os.path.join(self.module_dir, "foobar.ps1")
        yml_fn = os.path.join(self.module_dir, "foobar.yaml")

        docstring = {
            "DOCUMENTATION": {
                "module": "foobar",
                "short_description": "",
                "description": [],
                "options": {},
            }
        }

        # docs come from the yaml file so the
        # powershell file content is irrelevant
        with open(ps_fn, "w") as f:
            f.write("\n")

        with open(yml_fn, "w") as f:
            yaml.dump(docstring, f)

        contents = list(ContentFinder().find_contents(self.temp_dir))
        assert len(contents) == 1
        assert contents[0].path == "plugins/modules/foobar.ps1"
        assert contents[0].content_type.name == "MODULE"
        assert contents[0].content_type.value == "module"
        assert contents[0].content_type.category.name == "MODULE"


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


class TestPatternsFinder(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp()

        self.patterns_dir = os.path.join(self.path, "extensions", "patterns", "foo.bar")
        os.makedirs(self.patterns_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.path)

    @pytest.fixture(autouse=True)
    def inject_caplog(self, caplog):
        self._caplog = caplog

    def create_playbook(self, path, filename, content="---"):
        with open(os.path.join(path, filename), "w") as fh:
            fh.write(content)
            fh.flush()

    def create_readme(self, file="readme.md", content=""):
        with open(os.path.join(self.patterns_dir, file), "w") as fh:
            fh.write(content)
            fh.flush()

    def create_pattern(self, file="pattern.json", content=""):
        meta_path = os.path.join(self.patterns_dir, "meta")
        os.makedirs(meta_path, exist_ok=True)
        with open(os.path.join(meta_path, file), "w") as fh:
            fh.write(content)
            fh.flush()

    def test_missing_readme(self):
        readme_gen = PatternsFinder(self.path, log).find_readme(self.patterns_dir)
        with pytest.raises(ContentFindError) as exc:
            next(readme_gen)

        assert "extensions/patterns/foo.bar/readme(.md) not found" in str(exc.value)

    def test_find_readme(self):
        self.create_readme()
        readme_gen = PatternsFinder(self.path, log).find_readme(self.patterns_dir)
        readme = list(readme_gen)
        assert readme[0].content_type == constants.ContentType.PATTERNS
        assert readme[0].path == "extensions/patterns/foo.bar/readme.md"

    def test_missing_meta_dir(self):
        pattern_gen = PatternsFinder(self.path, log).find_meta_pattern(self.patterns_dir)
        with pytest.raises(ContentFindError) as exc:
            next(pattern_gen)

        assert "extensions/patterns/foo.bar/meta/pattern(.json) not found" in str(exc.value)

    def test_find_meta_pattern(self):
        self.create_pattern()
        pattern_gen = PatternsFinder(self.path, log).find_meta_pattern(self.patterns_dir)
        pattern = list(pattern_gen)
        assert pattern[0].content_type == constants.ContentType.PATTERNS
        assert pattern[0].path == "extensions/patterns/foo.bar/meta/pattern.json"

    def test_missing_playbooks_dir(self):
        playbooks_gen = PatternsFinder(self.path, log).find_playbooks(self.patterns_dir)
        with pytest.raises(ContentFindError) as exc:
            next(playbooks_gen)
        assert "extensions/patterns/foo.bar must contain playbooks directory" in str(exc.value)

    def test_no_playbooks_in_dir(self):
        playbooks_dir = os.path.join(self.patterns_dir, "playbooks")
        os.makedirs(playbooks_dir, exist_ok=True)

        playbooks_gen = PatternsFinder(self.path, log).find_playbooks(self.patterns_dir)
        with pytest.raises(ContentFindError) as exc:
            next(playbooks_gen)

        assert "extensions/patterns/foo.bar/playbooks must containt atleast one playbook" in str(
            exc.value
        )

    def test_find_playbooks(self):
        playboks_path = os.path.join(self.patterns_dir, "playbooks")
        os.makedirs(playboks_path, exist_ok=True)
        self.create_playbook(playboks_path, "playbook.yml")
        playbooks_gen = PatternsFinder(self.path, log).find_playbooks(self.patterns_dir)
        playbooks = list(playbooks_gen)

        assert playbooks[0].content_type == constants.ContentType.PATTERNS
        assert playbooks[0].path == "extensions/patterns/foo.bar/playbooks/playbook.yml"

    def test_missing_templates_dir(self):
        self._caplog.set_level(logging.INFO)
        with self._caplog.at_level(logging.INFO, logger="galaxy_importer.finder"):
            templates_gen = PatternsFinder(self.path, log).find_templates(self.patterns_dir)
            list(templates_gen)

        assert "extensions/patterns/foo.bar/templates not found, skipping" in self._caplog.text

    def test_empty_templates_dir(self):
        templates_path = os.path.join(self.patterns_dir, "templates")
        os.makedirs(templates_path, exist_ok=True)
        templates_gen = PatternsFinder(self.path, log).find_templates(self.patterns_dir)
        templates = list(templates_gen)

        assert len(templates) == 0

    def test_find_templates(self):
        templates_path = os.path.join(self.patterns_dir, "templates")
        os.makedirs(templates_path, exist_ok=True)
        self.create_playbook(templates_path, "template_01.yml")
        self.create_playbook(templates_path, "template_02.yml")
        templates_gen = PatternsFinder(self.path, log).find_templates(self.patterns_dir)
        templates = list(templates_gen)

        assert len(templates) == 2
        for template in templates:
            assert template.content_type == constants.ContentType.PATTERNS

        template_paths = [t.path for t in templates]
        assert "extensions/patterns/foo.bar/templates/template_01.yml" in template_paths
        assert "extensions/patterns/foo.bar/templates/template_02.yml" in template_paths
