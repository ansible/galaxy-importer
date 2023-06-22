import logging
import os
import shutil
from subprocess import TimeoutExpired
import tempfile
from types import SimpleNamespace
from unittest import mock

import pytest

from galaxy_importer import config
from galaxy_importer import exceptions as exc
from galaxy_importer.loaders import LegacyRoleLoader


META_YAML = """
dependencies: []

galaxy_info:
  role_name: my_role
  author: John Doe
  description: Some generic role description
  platforms:
    - name: Fedora
      versions: all
    - name: Debian
      versions:
        - buster
        - bullseye
  license: license (BSD, MIT)
  galaxy_tags:
    - web
    - system
    - server
"""

META_LINTPASS_YAML = """dependencies: []
galaxy_info:
  role_name: my_role
  author: author
  description: description
  license: MIT
  min_ansible_version: "2.0"
  platforms:
    - name: Fedora
      versions:
        - "16"
        - "17"
"""


README_MD = """
# my_role

Some generic readme for my_role
"""

README_HTML = """<h1>my_role</h1>
<p>Some generic readme for my_role</p>"""


@pytest.fixture
def tmp_role_root():
    try:
        tmp_dir = tempfile.TemporaryDirectory().name
        sub_path = os.path.join("ansible_roles", "my_role")
        role_root = os.path.join(tmp_dir, sub_path)
        os.makedirs(role_root)
        os.makedirs(os.path.join(role_root, "meta"))
        yield role_root
    finally:
        shutil.rmtree(tmp_dir)


@pytest.fixture
def populated_role_root(tmp_role_root):
    with open(os.path.join(tmp_role_root, "meta", "main.yml"), "w") as fh:
        fh.write(META_YAML)
    with open(os.path.join(tmp_role_root, "README.md"), "w") as fh:
        fh.write(README_MD)
    os.chdir(os.path.abspath(os.path.join(tmp_role_root, os.pardir)))
    return tmp_role_root


def test_load_values(populated_role_root):
    data = LegacyRoleLoader(
        populated_role_root,
        "my-namespace",
        cfg=SimpleNamespace(run_ansible_lint=False, ansible_local_tmp=populated_role_root),
    ).load()

    assert data.namespace == "my-namespace"
    assert data.name == "my_role"
    assert data.readme_file == "README.md"
    assert data.readme_html == README_HTML

    galaxy_info = data.metadata.galaxy_info
    assert galaxy_info.role_name == "my_role"
    assert galaxy_info.author == "John Doe"
    assert galaxy_info.description == "Some generic role description"
    assert galaxy_info.platforms == [
        {"name": "Fedora", "versions": "all"},
        {"name": "Debian", "versions": ["buster", "bullseye"]},
    ]
    assert galaxy_info.license == "license (BSD, MIT)"
    assert galaxy_info.galaxy_tags == ["web", "system", "server"]
    assert galaxy_info.company is None
    assert galaxy_info.issue_tracker_url is None
    assert galaxy_info.min_ansible_version is None
    assert galaxy_info.min_ansible_container_version is None
    assert galaxy_info.github_branch is None

    dependencies = data.metadata.dependencies
    assert dependencies == list()


@pytest.mark.parametrize(
    "invalid_namespace",
    [
        "",
        "a_b",
        "this--that",
        "foo-bar-",
        "-red-hat",
        "q" * 40,
    ],
)
def test_load_invalid_namespace(populated_role_root, invalid_namespace):
    with pytest.raises(exc.ImporterError, match=f"namespace {invalid_namespace} is invalid"):
        LegacyRoleLoader(populated_role_root, invalid_namespace).load()


def test_load_metadata_missing_yaml(populated_role_root):
    os.unlink(os.path.join(populated_role_root, "meta", "main.yml"))

    with pytest.raises(exc.ImporterError, match="Metadata not found"):
        LegacyRoleLoader(populated_role_root, "my-namespace")._load_metadata()


def test_load_metadata_location(populated_role_root):
    os.rename(
        os.path.join(populated_role_root, "meta", "main.yml"),
        os.path.join(populated_role_root, "meta", "main.yaml"),
    )

    data = LegacyRoleLoader(populated_role_root, "my-namespace").load()

    assert data.namespace == "my-namespace"

    os.rename(
        os.path.join(populated_role_root, "meta", "main.yaml"),
        os.path.join(populated_role_root, "meta.yml"),
    )

    data = LegacyRoleLoader(populated_role_root, "my-namespace").load()

    assert data.name == "my_role"

    os.rename(
        os.path.join(populated_role_root, "meta.yml"),
        os.path.join(populated_role_root, "meta.yaml"),
    )

    data = LegacyRoleLoader(populated_role_root, "my-namespace").load()

    assert data.readme_file == "README.md"


def test_load_metadata_invalid_metadata(populated_role_root):
    with open(os.path.join(populated_role_root, "meta", "main.yml"), "w") as fh:
        fh.write("")

    with pytest.raises(exc.ImporterError, match="must be in the form of a yaml dictionary"):
        LegacyRoleLoader(populated_role_root, "my-namespace").load()

    with open(os.path.join(populated_role_root, "meta", "main.yml"), "w") as fh:
        fh.write("hello: person\nanother: field\n")

    with pytest.raises(exc.ImporterError, match="galaxy_info field not found"):
        LegacyRoleLoader(populated_role_root, "my-namespace").load()

    with open(os.path.join(populated_role_root, "meta", "main.yml"), "w") as fh:
        fh.write("galaxy_info: nope\n")

    with pytest.raises(exc.ImporterError, match="galaxy_info field must contain a dictionary"):
        LegacyRoleLoader(populated_role_root, "my-namespace").load()

    with open(os.path.join(populated_role_root, "meta", "main.yml"), "w") as fh:
        fh.write("galaxy_info: \n  role_nam: my_role\n")

    with pytest.raises(exc.ImporterError, match="unknown field in galaxy_info"):
        LegacyRoleLoader(populated_role_root, "my-namespace").load()


@pytest.mark.parametrize(
    "name",
    [
        "my_role",
        "role1",
        "number_1",
        "directory",
        "etc",
    ],
)
def test_load_name_no_role_name(populated_role_root, name):
    with open(os.path.join(populated_role_root, "meta", "main.yml"), "w") as fh:
        fh.write("galaxy_info: \n  author: me\n")

    renamed_root = os.path.join(os.path.dirname(populated_role_root), name)
    os.rename(populated_role_root, renamed_root)

    data = LegacyRoleLoader(renamed_root, "my-namespace").load()

    assert data.name == name


def test_load_readme_missing(populated_role_root):
    os.unlink(os.path.join(populated_role_root, "README.md"))

    with pytest.raises(exc.ImporterError, match="No role readme found"):
        LegacyRoleLoader(populated_role_root, "my-namespace").load()


def test_lint_role_fail(populated_role_root, caplog):
    LegacyRoleLoader(
        populated_role_root,
        "my-namespace",
        cfg=SimpleNamespace(run_ansible_lint=True, ansible_local_tmp=populated_role_root),
    ).load()

    captured = caplog.text
    assert "WARNING" in captured
    assert len(caplog.records) > 0


def test_lint_role_pass(populated_role_root, caplog):
    with open(os.path.join(populated_role_root, "meta", "main.yml"), "w") as fh:
        fh.write(META_LINTPASS_YAML)

    LegacyRoleLoader(
        populated_role_root,
        "my-namespace",
        cfg=SimpleNamespace(run_ansible_lint=True, ansible_local_tmp=populated_role_root),
    ).load()

    assert len(caplog.records) == 0


def test_no_lint_role(populated_role_root, caplog):
    LegacyRoleLoader(
        populated_role_root,
        "my-namespace",
        cfg=SimpleNamespace(run_ansible_lint=False, ansible_local_tmp=populated_role_root),
    ).load()

    captured = caplog.text
    assert captured == ""
    assert len(caplog.records) == 0


@mock.patch("shutil.which")
def test_no_ansible_lint_bin(mocked_shutil_which, populated_role_root, caplog):
    mocked_shutil_which.return_value = False
    LegacyRoleLoader(
        populated_role_root,
        "my-namespace",
        cfg=SimpleNamespace(run_ansible_lint=True, ansible_local_tmp=populated_role_root),
    ).load()

    assert "ansible-lint not found, skipping lint of role" in caplog.text


@mock.patch("galaxy_importer.loaders.legacy_role.Popen.communicate")
def test_lint_timeout(mocked_communicate, populated_role_root, caplog):
    mocked_communicate.side_effect = TimeoutExpired(cmd="", timeout=120)

    with pytest.raises(TimeoutExpired):
        LegacyRoleLoader(
            populated_role_root,
            "my-namespace",
            cfg=SimpleNamespace(run_ansible_lint=True, ansible_local_tmp=populated_role_root),
        ).load()

    assert "Timeout on call to ansible-lint" in caplog.text


def test_no_config(populated_role_root):
    loader = LegacyRoleLoader(populated_role_root, "my-namespace", None, None)

    assert loader.cfg is not None
    assert isinstance(loader.cfg, config.Config)


def test_no_logger(populated_role_root):
    loader = LegacyRoleLoader(populated_role_root, "my-namespace", None, None)

    assert loader.log is not None
    assert isinstance(loader.log, logging.Logger)
