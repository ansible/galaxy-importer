import logging
import os
import pytest
import tempfile

from galaxy_importer import exceptions as exc
from galaxy_importer import markdown

log = logging.getLogger(__name__)

README_MD = """
# my_readme

Some generic readme
"""

README_HTML = """<h1>my_readme</h1>
<p>Some generic readme</p>"""


def test_convert_markdown(mocker):
    mocker.patch.object(markdown, "_convert_markdown")
    with tempfile.TemporaryDirectory() as tmp_dir:
        with open(os.path.join(tmp_dir, "README.md"), "w") as file:
            file.write(README_MD)
        markdown.convert_markdown(tmp_dir)
    assert markdown._convert_markdown.called


def test_convert_markdown_return():
    with tempfile.TemporaryDirectory() as tmp_dir:
        with open(os.path.join(tmp_dir, "README.md"), "w") as file:
            file.write(README_MD)
        data = markdown.convert_markdown(tmp_dir)
    assert isinstance(data, dict)
    assert "html" in data
    assert data["html"] == README_HTML


def test_convert_markdown_dir_dne():
    with (
        tempfile.TemporaryDirectory() as tmp_dir,
        pytest.raises(exc.ImporterError, match="does not exist"),
    ):
        markdown.convert_markdown(f"{tmp_dir}/does/not/exist")


def test_convert_markdown_readme_dne():
    with tempfile.TemporaryDirectory() as tmp_dir:
        with open(os.path.join(tmp_dir, "README.html"), "w") as file:
            file.write(README_MD)
        with pytest.raises(exc.ImporterError, match="Path does not contain README"):
            markdown.convert_markdown(tmp_dir)
