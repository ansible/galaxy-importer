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
import shutil
import tempfile
import unittest

import pytest

from galaxy_importer.finder import ContentFinder
from galaxy_importer import exceptions as exc


class TestContentFinder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        os.mkdir(os.path.join(self.temp_dir, 'plugins'))
        self.module_dir = os.path.join(self.temp_dir, 'plugins', 'modules')
        os.mkdir(self.module_dir)

        self.role_dir = os.path.join(self.temp_dir, 'roles')
        os.mkdir(self.role_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_find_content(self):
        with open(os.path.join(self.module_dir, '__init__.py'), 'w'):
            pass
        with open(os.path.join(self.module_dir, 'first_module.py'), 'w'):
            pass
        with open(os.path.join(self.module_dir, 'second_module.py'), 'w'):
            pass

        my_role_dir = os.path.join(self.role_dir, 'my_role')
        os.mkdir(my_role_dir)

        contents = ContentFinder().find_contents(self.temp_dir)

        content_items = [os.path.basename(c.path) for c in contents]
        assert 'first_module.py' in content_items
        assert 'second_module.py' in content_items
        assert '__init__.py' not in content_items
        assert 'my_role' in content_items

    def test_find_no_content(self):
        contents = ContentFinder().find_contents(self.temp_dir)
        assert not any(True for _ in contents)

    def test_skip_plugin_files(self):
        with open(os.path.join(self.module_dir, '__init__.py'), 'w'):
            pass
        with open(os.path.join(self.module_dir, 'main.go'), 'w'):
            pass
        contents = ContentFinder().find_contents(self.temp_dir)
        assert not any(True for _ in contents)

    def test_error_nested_plugin(self):
        my_nested_module = os.path.join(self.module_dir, 'another_dir')
        os.mkdir(my_nested_module)
        with pytest.raises(
                exc.ContentFindError, match='Nested plugins not supported'):
            ContentFinder().find_contents(self.temp_dir)

    def test_error_file_in_roles_dir(self):
        with open(os.path.join(self.role_dir, 'main.yml'), 'w'):
            pass
        with pytest.raises(exc.ContentFindError, match='File inside "roles"'):
            ContentFinder().find_contents(self.temp_dir)
