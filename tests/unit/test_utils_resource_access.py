# test_resource_access.py

import glob
import json
import os
from unittest.mock import patch

from galaxy_importer.utils.resource_access import resource_stream_compat, resource_filename_compat


@patch("galaxy_importer.utils.resource_access.USE_PKG_RESOURCES", True)
@patch("galaxy_importer.utils.resource_access.pkg_resources")
def test_resource_stream_compat_with_pkg_resources(mock_pkg_resources):
    with resource_stream_compat(
        "galaxy_importer.utils.spdx_licenses", "spdx_licenses.json"
    ) as fstream:
        raw = fstream.read()
    assert raw is not None
    assert mock_pkg_resources.resource_stream.called


@patch("galaxy_importer.utils.resource_access.USE_PKG_RESOURCES", False)
@patch("galaxy_importer.utils.resource_access.files")
def test_resource_stream_compat_with_importlib(mock_files):
    with resource_stream_compat(
        "galaxy_importer.utils.spdx_licenses", "spdx_licenses.json"
    ) as fstream:
        raw = fstream.read()
    assert raw is not None
    assert mock_files.called


@patch("galaxy_importer.utils.resource_access.USE_PKG_RESOURCES", True)
@patch("galaxy_importer.utils.resource_access.pkg_resources")
def test_resource_filename_compat_with_pkg_resources(mock_pkg_resources):
    with resource_filename_compat(
        "galaxy_importer.utils.spdx_licenses", "spdx_licenses.json"
    ) as fstream:
        raw = fstream.read()
    assert raw is not None
    assert mock_pkg_resources.resource_filename.called


@patch("galaxy_importer.utils.resource_access.USE_PKG_RESOURCES", False)
def test_resource_filename_compat_with_importlib_filename():
    with resource_filename_compat(
        "galaxy_importer.utils.spdx_licenses", "spdx_licenses.json"
    ) as fpath:
        with open(fpath, "r") as f:
            ds = json.loads(f.read())
    assert fpath.endswith("spdx_licenses.json")
    assert isinstance(ds, dict)


@patch("galaxy_importer.utils.resource_access.USE_PKG_RESOURCES", False)
def test_resource_filename_compat_with_importlib_dirname():
    with resource_filename_compat("galaxy_importer.ansible_test", "container") as fpath:
        filenames = glob.glob(f"{fpath}/*")
    filenames = [os.path.basename(x) for x in filenames]
    assert len(filenames) == 3
    assert "Dockerfile" in filenames
    assert "entrypoint.sh" in filenames
