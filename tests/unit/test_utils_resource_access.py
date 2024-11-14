# test_resource_access.py

import glob
import json
import os

from galaxy_importer.utils.resource_access import resource_filename_compat


def test_resource_filename_compat_with_importlib_filename():
    with resource_filename_compat("galaxy_importer.utils", "spdx_licenses.json") as fpath:
        with open(fpath, "r") as f:
            ds = json.loads(f.read())
    assert fpath.endswith("spdx_licenses.json")
    assert isinstance(ds, dict)


def test_resource_filename_compat_with_importlib_dirname():
    with resource_filename_compat("galaxy_importer.ansible_test", "container") as fpath:
        filenames = glob.glob(f"{fpath}/*")
    filenames = [os.path.basename(x) for x in filenames]
    assert len(filenames) == 3
    assert "Dockerfile" in filenames
    assert "entrypoint.sh" in filenames
