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

import collections
import os
from unittest import mock

from pyfakefs.fake_filesystem_unittest import TestCase
import pytest

from galaxy_importer.utils import markup as markup_utils

TEXT_SIMPLE = 'A simple description'
TEXT_BAD_TAG = 'hello <script>cruel</script> world'
TEXT_BAD_HTML_IN_MD = '''
> hello <a name="n"
> href="javascript:something_bad()">*you*</a>
'''
TEXT_FORMATTING = '''
# Role

[Tool](https://www.example.com) installed in `$PATH`

### Installation

    package_version: "1.2.0"

> NOTE: Tool 'feature' is _beta_

* Item1
* Item2
'''

DocFile = collections.namedtuple('DocFile', ['text', 'mimetype'])


class TestFindGetFiles(TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.directory = '/tmp'

    def test_find_readme(self):
        assert not markup_utils._find_readme(self.directory)
        file_path = os.path.join(self.directory, 'README.md')
        self.fs.create_file(file_path)
        res = markup_utils._find_readme(self.directory)
        assert res == '/tmp/README.md'

    def test_cannot_find_invalid_readmes(self):
        for invalid_name in [
            'readme.md',
            'README',
            'README.rst',
            'readme',
            'INTRO.md',
        ]:
            self.fs.create_file(os.path.join(self.directory, invalid_name))

        assert not markup_utils._find_readme(self.directory)

    def test_get_readme_doc_file(self):
        res = markup_utils.get_readme_doc_file(self.directory)
        assert res is None

        file_path = os.path.join(self.directory, 'README.md')
        self.fs.create_file(file_path, contents='## My Collection')
        res = markup_utils.get_readme_doc_file(self.directory)
        assert res.name == 'README.md'
        assert res.text == '## My Collection'

    def test_get_file(self):
        filename = 'README.md'
        res = markup_utils._get_file(self.directory, filename)
        assert res is None

        file_path = os.path.join(self.directory, filename)
        self.fs.create_file(file_path)
        res = markup_utils._get_file(self.directory, file_path)
        assert res.name == 'README.md'

    @mock.patch('os.path.getsize')
    def test_get_file_with_file_size_error(self, getsize):
        getsize.return_value = (512 ** 2) + 1
        filename = 'README.md'
        file_path = os.path.join(self.directory, filename)
        self.fs.create_file(file_path)
        with pytest.raises(markup_utils.FileSizeError):
            markup_utils._get_file(self.directory, file_path)

    def test_get_doc_files(self):
        res = markup_utils.get_doc_files(self.directory)
        assert res is None

        for doc_file in [
            'GETTING_STARTED.md',
            'DEEP_DIVE.md',
            'WHOOPS.txt',
            'EXAMPLES.md',
        ]:
            self.fs.create_file(os.path.join(self.directory, doc_file))

        self.fs.create_dir(os.path.join(self.directory, 'sub_dir_to_ignore'))
        res = markup_utils.get_doc_files(self.directory)
        assert len(res) == 3
        names = [d.name for d in res]
        assert 'GETTING_STARTED.md' in names
        assert 'DEEP_DIVE.md' in names
        assert 'EXAMPLES.md' in names
        assert 'WHOOPS.txt' not in names

    def test_find_doc_files_no_dir(self):
        res = markup_utils._find_doc_files(directory='/does_not_exist')
        assert res == []


class TestHtmlRender(TestCase):
    def call_render(self, raw_text, mimetype):
        doc_file = DocFile(text=raw_text, mimetype=mimetype)
        return markup_utils._render_from_markdown(doc_file)

    def test_get_html(self):
        doc_file = DocFile(text=TEXT_SIMPLE, mimetype='text/markdown')
        html = markup_utils.get_html(doc_file)
        assert html == '<p>{}</p>'.format(TEXT_SIMPLE)

        doc_file = DocFile(text=TEXT_SIMPLE, mimetype='text/rst')
        html = markup_utils.get_html(doc_file)
        assert html is None

    def test_render_simple(self):
        html = self.call_render(TEXT_SIMPLE, 'text/markdown')
        assert html == '<p>{}</p>'.format(TEXT_SIMPLE)

    def test_render_bad_tag(self):
        html = self.call_render(TEXT_BAD_TAG, 'text/markdown')
        assert '<script>' not in html

    def test_render_bad_html_hidden_in_md(self):
        html = self.call_render(TEXT_BAD_HTML_IN_MD, 'text/markdown')
        assert 'javascript' not in html

    def test_render_formatting(self):
        html = self.call_render(TEXT_FORMATTING, 'text/markdown')
        assert '<h1>Role</h1>' in html
        assert '<a href="https://www.example.com">Tool</a>' in html
        assert '<code>$PATH</code>' in html
        assert '<h3>Installation</h3>' in html
        assert '<code>package_version: "1.2.0"' in html
        assert '<blockquote>\n<p>NOTE:' in html
        assert 'Tool \'feature\' is <em>beta</em>' in html
        assert '<ul>\n<li>Item1</li>' in html
