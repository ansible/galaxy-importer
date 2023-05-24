import os
import pytest
import shutil
import tempfile
from types import SimpleNamespace

from galaxy_importer import config
from galaxy_importer import exceptions as exc
from galaxy_importer import legacy_role


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
    return tmp_role_root


def test_import_legacy_role(mocker):
    mocker.patch.object(legacy_role, "_import_legacy_role")
    mocker.patch.object(config.ConfigFile, "load")
    legacy_role.import_legacy_role(populated_role_root, "my-namespace", logger=None, cfg=None)
    assert config.ConfigFile.load.called
    assert legacy_role._import_legacy_role.called


def test_import_legacy_role_return(populated_role_root):
    data = legacy_role.import_legacy_role(
        populated_role_root,
        "my-namespace",
        None,
        SimpleNamespace(run_ansible_lint=False, ansible_local_tmp=populated_role_root),
    )

    assert isinstance(data, dict)
    assert "metadata" in data
    assert "galaxy_info" in data["metadata"]
    assert "dependencies" in data["metadata"]
    assert data["metadata"]["dependencies"] == list()
    assert data["metadata"]["galaxy_info"]["role_name"] == "my_role"
    assert data["metadata"]["galaxy_info"]["galaxy_tags"] == ["web", "system", "server"]
    assert data["metadata"]["galaxy_info"]["platforms"] == [
        {"name": "Fedora", "versions": "all"},
        {"name": "Debian", "versions": ["buster", "bullseye"]},
    ]


def test__import_legacy_role_return(populated_role_root):
    data = legacy_role._import_legacy_role(
        populated_role_root,
        "my-namespace",
        None,
        SimpleNamespace(run_ansible_lint=False, ansible_local_tmp=populated_role_root),
    )

    assert isinstance(data, dict)
    assert "metadata" in data
    assert "galaxy_info" in data["metadata"]
    assert "dependencies" in data["metadata"]
    assert data["metadata"]["dependencies"] == list()
    assert data["metadata"]["galaxy_info"]["role_name"] == "my_role"
    assert data["metadata"]["galaxy_info"]["galaxy_tags"] == ["web", "system", "server"]
    assert data["metadata"]["galaxy_info"]["platforms"] == [
        {"name": "Fedora", "versions": "all"},
        {"name": "Debian", "versions": ["buster", "bullseye"]},
    ]


def test_import_legacy_no_namespace():
    with pytest.raises(exc.ImporterError, match="requires explicit namespace"):
        legacy_role.import_legacy_role(populated_role_root, None, None, None)
