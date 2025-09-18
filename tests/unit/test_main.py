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
import re

from galaxy_importer import main


def test_parser():
    parser = main.parse_args(["path/to/my_file.tar.gz"])
    assert parser.file == "path/to/my_file.tar.gz"
    assert not parser.print_result

    parser = main.parse_args(["my_file.tar.gz", "--print-result"])
    assert parser.file == "my_file.tar.gz"
    assert parser.print_result

    parser = main.parse_args(["--git-clone-path=/my/clone/path", "--output-path=/my/output/path"])
    assert not parser.file
    assert parser.git_clone_path == "/my/clone/path"
    assert parser.output_path == "/my/output/path"

    parser = main.parse_args(["--namespace", "my-namespace", "--legacy-role"])
    assert parser.namespace == "my-namespace"
    assert parser.legacy_role


def test_main_no_args():
    with pytest.raises(
        TypeError, match=re.escape("expected str, bytes or os.PathLike object, not NoneType")
    ):
        main.main(args={})


def test_legacy_no_role(caplog):
    args = main.parse_args(["--legacy-role"])
    data = main.call_importer(args, None)
    assert data is None
    assert "supply the directory of the role" in caplog.text
    assert len(caplog.records) == 1


def test_legacy_missing_namespace(caplog):
    args = main.parse_args(["--legacy-role", "role"])
    data = main.call_importer(args, None)
    assert data is None
    assert "requires explicit namespace" in caplog.text
    assert len(caplog.records) == 1


def test_markdown_no_directory(caplog):
    args = main.parse_args(["--markdown"])
    data = main.call_importer(args, None)
    assert data is None
    assert "Must supply the directory of README" in caplog.text
    assert len(caplog.records) == 1
