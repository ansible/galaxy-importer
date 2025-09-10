import pytest
from unittest.mock import patch

from galaxy_importer.utils.lint_version import is_lint_patterns_supported, is_patterns_load_enabled
from galaxy_importer import config


@patch("galaxy_importer.utils.lint_version.get_version_from_metadata")
@pytest.mark.parametrize(
    ("lint_version", "enabled"),
    [
        ("25.6.9", False),
        ("25.7.0", True),
        ("25.8.0", True),
    ],
)
def test_is_lint_patterns_supported(mock_lint_version, lint_version, enabled):
    mock_lint_version.return_value = lint_version
    assert is_lint_patterns_supported() is enabled


@patch("galaxy_importer.utils.lint_version.get_version_from_metadata")
def test_is_patterns_load_enabled_default(lint_version):
    lint_version.return_value = "25.7.0"
    cfg = config.Config(config_data=config.ConfigFile.load())
    assert cfg.patterns is False
    assert is_patterns_load_enabled() is False


@patch("galaxy_importer.utils.lint_version.get_version_from_metadata")
@pytest.mark.parametrize(
    "patterns_cfg",
    [
        True,
        False,
    ],
)
def test_is_patterns_load_enabled_true(lint_version, monkeypatch, patterns_cfg):
    lint_version.return_value = "25.8.2"
    monkeypatch.setenv("GALAXY_IMPORTER_PATTERNS", patterns_cfg)

    cfg = config.Config(config_data=config.ConfigFile.load())
    assert cfg.patterns is patterns_cfg

    assert is_patterns_load_enabled() is patterns_cfg
