import re

import pytest

from galaxy_importer import exceptions as exc
from galaxy_importer.schema import LegacyGalaxyInfo, LegacyMetadata, LegacyImportResult


@pytest.fixture
def galaxy_info():
    info = {
        "role_name": "my_role",
        "author": "shakespeare",
        "description": "incredible role",
        "company": "Red Hat",
        "issue_tracker_url": "https://www.github.com",
        "license": "MIT",
        "min_ansible_version": "2.4",
        "min_ansible_container_version": "2.0",
        "platforms": [
            {"name": "Fedora", "versions": "all"},
            {"name": "Debian", "versions": "['7.0']"},
        ],
        "galaxy_tags": ["docker", "ansible", "container"],
    }
    return info


def test_values(galaxy_info):
    info = LegacyGalaxyInfo(**galaxy_info)

    assert info.role_name == "my_role"
    assert info.author == "shakespeare"
    assert info.description == "incredible role"
    assert info.company == "Red Hat"
    assert info.issue_tracker_url == "https://www.github.com"
    assert info.license == "MIT"
    assert info.min_ansible_version == "2.4"
    assert info.min_ansible_container_version == "2.0"
    assert info.github_branch is None
    assert info.platforms == [
        {"name": "Fedora", "versions": "all"},
        {"name": "Debian", "versions": "['7.0']"},
    ]
    assert info.galaxy_tags == ["docker", "ansible", "container"]


def test_valid_str(galaxy_info):
    galaxy_info["role_name"] = []
    with pytest.raises(exc.LegacyRoleSchemaError, match="must be a string"):
        LegacyGalaxyInfo(**galaxy_info)


def test_valid_list_dict(galaxy_info):
    galaxy_info["platforms"] = "string"
    with pytest.raises(exc.LegacyRoleSchemaError, match=re.compile("must be a list$")):
        LegacyGalaxyInfo(**galaxy_info)

    galaxy_info["platforms"] = ["string", "other"]
    with pytest.raises(exc.LegacyRoleSchemaError, match="must be a list of dictionaries"):
        LegacyGalaxyInfo(**galaxy_info)


def test_valid_list_str(galaxy_info):
    galaxy_info["galaxy_tags"] = "string"
    with pytest.raises(exc.LegacyRoleSchemaError, match=re.compile("must be a list$")):
        LegacyGalaxyInfo(**galaxy_info)

    galaxy_info["galaxy_tags"] = [{}]
    with pytest.raises(exc.LegacyRoleSchemaError, match="must be a list of strings"):
        LegacyGalaxyInfo(**galaxy_info)


@pytest.mark.parametrize(
    "valid_name",
    [
        "this",
        "that",
        "walker_turzai",
        "foo_bar_baz",
        "name123_four",
        "r1",
        "crush_",
        "3w6",
        "-foo-bar_baz-",
        "___---___",
        "9",
        "q" * 55,
    ],
)
def test_valid_role_name(galaxy_info, valid_name):
    galaxy_info["role_name"] = valid_name
    info = LegacyGalaxyInfo(**galaxy_info)
    assert info.role_name == valid_name


@pytest.mark.parametrize(
    "invalid_name",
    [
        "$@#",
        "this.role",
        "docker!",
        "big space",
        "q" * 56,
    ],
)
def test_invalid_role_name(galaxy_info, invalid_name):
    galaxy_info["role_name"] = invalid_name
    with pytest.raises(
        exc.LegacyRoleSchemaError, match=re.escape(f"role name {invalid_name} is invalid")
    ):
        LegacyGalaxyInfo(**galaxy_info)


def test_max_author(galaxy_info):
    galaxy_info["author"] = galaxy_info["author"] * 100
    with pytest.raises(exc.LegacyRoleSchemaError, match="must not exceed"):
        LegacyGalaxyInfo(**galaxy_info)


def test_max_description(galaxy_info):
    galaxy_info["description"] = "Description!" * 100
    with pytest.raises(exc.LegacyRoleSchemaError, match="must not exceed"):
        LegacyGalaxyInfo(**galaxy_info)


def test_max_company(galaxy_info):
    galaxy_info["company"] = "Red Hat" * 10
    with pytest.raises(exc.LegacyRoleSchemaError, match="must not exceed"):
        LegacyGalaxyInfo(**galaxy_info)


def test_max_url(galaxy_info):
    galaxy_info["issue_tracker_url"] = galaxy_info["issue_tracker_url"] + ("/a" * 1001)
    with pytest.raises(exc.LegacyRoleSchemaError, match="must not exceed"):
        LegacyGalaxyInfo(**galaxy_info)


def test_max_license(galaxy_info):
    galaxy_info["license"] = galaxy_info["license"] * 30
    with pytest.raises(exc.LegacyRoleSchemaError, match="must not exceed"):
        LegacyGalaxyInfo(**galaxy_info)


def test_max_version(galaxy_info):
    galaxy_info["min_ansible_version"] = galaxy_info["min_ansible_version"] * 50
    with pytest.raises(exc.LegacyRoleSchemaError, match="must not exceed"):
        LegacyGalaxyInfo(**galaxy_info)

    galaxy_info["min_ansible_version"] = "2.1"
    galaxy_info["min_ansible_container_version"] = galaxy_info["min_ansible_container_version"] * 50
    with pytest.raises(exc.LegacyRoleSchemaError, match="must not exceed"):
        LegacyGalaxyInfo(**galaxy_info)


def test_max_tag(galaxy_info):
    galaxy_info["galaxy_tags"][0] = "rhel" * 100
    with pytest.raises(exc.LegacyRoleSchemaError, match="must not exceed"):
        LegacyGalaxyInfo(**galaxy_info)


@pytest.mark.parametrize(
    "valid_dependency",
    [
        [],
        ["geerlingguy.php"],
        ["eamontracey.hello_role"],
        ["geerlingguy.php", "eamontracey.hello_role"],
    ],
)
def test_valid_dependencies(galaxy_info, valid_dependency):
    metadata = LegacyMetadata(LegacyGalaxyInfo(**galaxy_info), valid_dependency)
    assert metadata.dependencies == valid_dependency


@pytest.mark.parametrize(
    "invalid_dependency",
    [
        "geerlingguy.java",
        {"name": "redhat.ansible"},
        {"role": "redhat.ansible"},
        [[]],
    ],
)
def test_invalid_dependency_type(galaxy_info, invalid_dependency):
    with pytest.raises(
        exc.LegacyRoleSchemaError,
        match="must be either a list of strings or a list of dictionaries.",
    ):
        LegacyMetadata(LegacyGalaxyInfo(**galaxy_info), invalid_dependency)


@pytest.mark.parametrize(
    "invalid_dict",
    [
        [{}],
        [{"role_name": "foo.bar"}],
        [
            {
                "tags": ["nodejs"],
                "vars": {"ignore_errors": "{{ ansible_check_mode }}"},
            }
        ],
    ],
)
def test_invalid_dependency_dict_type(galaxy_info, invalid_dict):
    with pytest.raises(
        exc.LegacyRoleSchemaError,
        match="dependency must include either the 'role,' 'name,' or 'src' keyword.",
    ):
        LegacyMetadata(LegacyGalaxyInfo(**galaxy_info), invalid_dict)


@pytest.mark.parametrize(
    "dependencies",
    [
        ["geerlingguy.nodejs"],
        [{"role": "foo.bar"}],
        [{"name": "geerlingguy.docker"}],
        [{"src": "galaxy.role,version,name"}],
        [
            {
                "role": "geerlingguy.nodejs",
                "tags": ["nodejs"],
                "vars": {"ignore_errors": "{{ ansible_check_mode }}"},
            }
        ],
    ],
)
def test_valid_dependency_types(galaxy_info, dependencies):
    legacy_metadata = LegacyMetadata(LegacyGalaxyInfo(**galaxy_info), dependencies)
    assert isinstance(legacy_metadata.dependencies, list)
    for dep in legacy_metadata.dependencies:
        assert isinstance(dep, dict) or isinstance(dep, str)


def test_invalid_dependency_separation(galaxy_info):
    dependencies = ["foo.bar.baz"]

    with pytest.raises(exc.LegacyRoleSchemaError, match="namespace and name separated by '.'"):
        LegacyMetadata(LegacyGalaxyInfo(**galaxy_info), dependencies)


@pytest.mark.parametrize(
    "dependencies",
    [
        ["someone.my_role"],
        [{"role": "someone.my_role"}],
        [{"name": "someone.my_role"}],
        [{"src": "someone.my_role"}],
    ],
)
def test_self_dependency(galaxy_info, dependencies):
    with pytest.raises(exc.LegacyRoleSchemaError, match="cannot depend on itself"):
        LegacyImportResult(
            "someone",
            "my_role",
            LegacyMetadata(LegacyGalaxyInfo(**galaxy_info), dependencies),
            "README.md",
            "",
        )


@pytest.mark.parametrize(
    "invalid_name",
    [
        "$@#",
        "this.role",
        "docker!",
        "big space",
        "q" * 56,
    ],
)
def test_load_name_regex(galaxy_info, invalid_name):
    with pytest.raises(
        exc.LegacyRoleSchemaError, match=re.escape(f"role name {invalid_name} is invalid")
    ):
        LegacyImportResult("my-namespace", invalid_name, LegacyMetadata(galaxy_info, []))


# https://github.com/ansible/galaxy-importer/pull/241
@pytest.mark.parametrize(
    "invalid_namespace",
    [
        "_Harsha_",
        "mhabrnal@redhat.com",
        "/etc/ansible/roles/tt-test.nfs",
        "rohitggarg/docker-swarm#",
        "-role-name",
    ],
)
def test_invalid_namespace(galaxy_info, invalid_namespace):
    galaxy_info.update({"namespace": invalid_namespace})

    with pytest.raises(
        exc.LegacyRoleSchemaError, match=re.escape(f"namespace {invalid_namespace} is invalid")
    ):
        LegacyGalaxyInfo(**galaxy_info)


@pytest.mark.parametrize(
    "valid_namespace",
    [
        "george.shuklin",
        "pilou-",
        "gh_harsha_",
        "get-external-ip-via-dyndns",
        "inventory_to_hostname",
    ],
)
def test_valid_namespace(galaxy_info, valid_namespace):
    galaxy_info.update({"namespace": valid_namespace})
    assert valid_namespace == LegacyGalaxyInfo(**galaxy_info).namespace
