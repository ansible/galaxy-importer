# resource_access.py

import tempfile
import shutil
import os

from importlib.resources import files

from contextlib import contextmanager


@contextmanager
def resource_filename_compat(package, resource_name):
    """
    A context manager to provide a file path to a package resource, abstracting over
    `pkg_resources.resource_filename` and `importlib.resources`.

    Args:
        package (str): The name of the package containing the resource.
        resource_name (str): The name of the resource within the package.

    Yields:
        str: The file path to the resource.
    """

    with tempfile.TemporaryDirectory() as temp_dir:
        resource_path = files(package) / resource_name
        if resource_path.is_dir():
            # Copy directory content to temp_dir if resource is a directory
            shutil.copytree(
                resource_path,
                os.path.join(temp_dir, os.path.basename(resource_path)),
                dirs_exist_ok=True,
            )
            yield os.path.join(temp_dir, os.path.basename(resource_path))
        else:
            # Copy file to temp_dir if resource is a file
            temp_path = os.path.join(temp_dir, os.path.basename(resource_name))
            shutil.copy2(resource_path, temp_path)
            yield temp_path
