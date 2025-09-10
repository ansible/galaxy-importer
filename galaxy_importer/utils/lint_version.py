from packaging.version import Version
from importlib.metadata import version, PackageNotFoundError

from galaxy_importer import constants, config


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


def is_patterns_load_enabled():
    cfg = config.Config(config_data=config.ConfigFile.load())
    return cfg.patterns is True and is_lint_patterns_supported()
