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
import hashlib
import mimetypes
import os

import markdown
import bleach
from bleach_whitelist import markdown_tags, markdown_attrs

README_NAME = 'README'
DOCFILE_EXTENSIONS = [
    '.md',
]
DOCFILE_MIMETYPES = {
    '.md': 'text/markdown',
}
DOCFILE_MAX_SIZE = 512 ** 2  # 512 KiB

DocFile = collections.namedtuple(
    'DocFile', ['name', 'text', 'mimetype', 'hash']
)

for _ext, _type in DOCFILE_MIMETYPES.items():
    mimetypes.add_type(_type, _ext)


class FileSizeError(Exception):
    pass


def get_readme_doc_file(directory):
    filename = _find_readme(directory)
    if not filename:
        return None
    return _get_file(directory, filename)


def get_doc_files(directory):
    filenames = _find_doc_files(directory)
    if not filenames:
        return None
    return [_get_file(directory, f) for f in filenames]


def get_html(doc_file):
    if doc_file.mimetype == 'text/markdown':
        return _render_from_markdown(doc_file)
    return None


def _find_readme(directory):
    for ext in DOCFILE_EXTENSIONS:
        filename = os.path.join(directory, README_NAME + ext)
        if os.path.exists(filename):
            return filename
    return None


def _find_doc_files(directory):
    result = []
    if not os.path.exists(directory):
        return result
    for filename in os.listdir(directory):
        if not os.path.isfile(os.path.join(directory, filename)):
            continue
        mimetype, _ = mimetypes.guess_type(filename)
        if mimetype not in DOCFILE_MIMETYPES.values():
            continue
        result.append(os.path.join(directory, filename))
    return result


def _get_file(directory, filename):
    if not os.path.exists(filename):
        return None

    if os.path.getsize(filename) > DOCFILE_MAX_SIZE:
        raise FileSizeError(
            'Documentation file "{0}" is bigger than 512 KiB.'
            .format(os.path.relpath(filename, directory)))

    mimetype, encoding = mimetypes.guess_type(filename)

    with open(filename, 'rb') as fp:
        raw_text = fp.read()
    hash_ = hashlib.sha256(raw_text).hexdigest()

    return DocFile(
        name=os.path.basename(filename),
        text=raw_text.decode('utf-8'),
        mimetype=mimetype,
        hash=hash_
    )


def _render_from_markdown(doc_file):
    # notes on bleach coming after markdown, and bleach_whitelist pkg:
    # https://github.com/Python-Markdown/markdown/issues/225
    unsafe_html = markdown.markdown(doc_file.text, extensions=['extra'])
    return bleach.clean(
        unsafe_html,
        tags=markdown_tags + ['pre'],
        attributes=markdown_attrs,
        styles=[],
        strip=True
    )
