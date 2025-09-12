from importlib.metadata import version, PackageNotFoundError
from packaging.version import Version
from galaxy_importer import constants


def get_version_from_metadata(package_name):
    """Uses importlib.metadata.version to retrieve package version"""
    try:
        return version(package_name)
    except PackageNotFoundError:
        return ""


def is_lint_patterns_supported():
    """
    minimum ansible-lint version that supports patterns validating is >=25.7.0.
    importer must skip loading/parsing patterns directory if ansible-lint
    version doesn't support patterns.
    """
    return Version(get_version_from_metadata("ansible-lint")) >= Version(
        constants.MIN_ANSIBLE_LINT_PATTERNS_VERSION
    )
