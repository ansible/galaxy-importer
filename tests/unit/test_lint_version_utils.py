import pytest
from unittest.mock import patch

from galaxy_importer.utils.lint_version import is_lint_patterns_supported


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
