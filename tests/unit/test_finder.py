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

from galaxy_importer.finder import ContentFinder


class TestContentFinder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        os.mkdir(os.path.join(self.temp_dir, 'plugins'))
        self.module_dir = os.path.join(self.temp_dir, 'plugins', 'modules')
        os.mkdir(self.module_dir)

        self.roles_dir = os.path.join(self.temp_dir, 'roles')
        os.mkdir(self.roles_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_find_content(self):
        with open(os.path.join(self.module_dir, '__init__.py'), 'w'):
            pass
        with open(os.path.join(self.module_dir, 'first_module.py'), 'w'):
            pass
        with open(os.path.join(self.module_dir, 'second_module.py'), 'w'):
            pass

        my_roles_dir = os.path.join(self.roles_dir, 'my_role')
        os.mkdir(my_roles_dir)
        os.mkdir(os.path.join(my_roles_dir, 'tasks'))

        contents = ContentFinder().find_contents(self.temp_dir)

        content_items = [os.path.basename(c.path) for c in contents]
        assert 'first_module.py' in content_items
        assert 'second_module.py' in content_items
        assert '__init__.py' not in content_items
        assert 'my_role' in content_items
        assert len(content_items) == 3

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

    def test_nested_plugin(self):
        subdir1 = os.path.join(self.module_dir, 'subdir1')
        os.mkdir(subdir1)
        subdir2 = os.path.join(subdir1, 'subdir2')
        os.mkdir(subdir2)
        with open(os.path.join(subdir2, 'nested_module.py'), 'w'):
            pass

        contents = ContentFinder().find_contents(self.temp_dir)
        assert list(contents)[0].path == \
            'plugins/modules/subdir1/subdir2/nested_module.py'

    def test_nested_role(self):
        subdir1 = os.path.join(self.roles_dir, 'subdir1')
        os.mkdir(subdir1)
        role_dir = os.path.join(subdir1, 'my_role')
        os.mkdir(role_dir)

        contents = ContentFinder().find_contents(self.temp_dir)
        assert len(contents) == 0

        dir_in_role = os.path.join(role_dir, 'tasks')
        os.mkdir(dir_in_role)

        contents = ContentFinder().find_contents(self.temp_dir)
        assert list(contents)[0].path == \
            'roles/subdir1/my_role'

    def test_error_file_in_roles_dir(self):
        with open(os.path.join(self.roles_dir, 'main.yml'), 'w'):
            pass
        my_roles_dir = os.path.join(self.roles_dir, 'my_role')
        os.mkdir(my_roles_dir)
        os.mkdir(os.path.join(my_roles_dir, 'tasks'))

        contents = ContentFinder().find_contents(self.temp_dir)
        content_items = [os.path.basename(c.path) for c in contents]
        assert 'my_role' in content_items
        assert len(content_items) == 1
