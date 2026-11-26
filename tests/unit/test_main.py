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

import re

import pytest
from pytest_mock import MockerFixture

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


@pytest.mark.parametrize(
    ("cli_args", "expected"),
    [([], 0), (["--fail-on-error"], 1)],
)
def test_main_fail_on_logged_error(
    mocker: MockerFixture, cli_args: list[str], expected: int
) -> None:
    mocker.patch.object(main, "setup_logger")
    mocker.patch.object(main, "write_output_file")

    def import_with_error(*args: object, **kwargs: object) -> dict[str, bool]:
        main.logger.error("expected error")
        return {"ok": True}

    mocker.patch.object(main, "call_importer", side_effect=import_with_error)

    assert main.main(["artifact.tar.gz", *cli_args]) == expected


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
