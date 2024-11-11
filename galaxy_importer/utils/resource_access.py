# resource_access.py

import tempfile
import shutil
import os


try:
    from pkg_resources import resource_stream
    USE_PKG_RESOURCES = True
except ImportError:
    from importlib.resources import files
    USE_PKG_RESOURCES = False

from contextlib import contextmanager


@contextmanager
def resource_stream_compat(package, resource_name):
    """
    A context manager to provide a stream to a package resource, abstracting over
    `pkg_resources.resource_stream` and `importlib.resources`.

    Args:
        package (str): The name of the package containing the resource.
        resource_name (str): The name of the resource within the package.

    Yields:
        A file-like object for reading the resource.
    """
    if USE_PKG_RESOURCES:
        # Use pkg_resources.resource_stream if available
        stream = resource_stream(package, resource_name)
    else:
        # Fallback to importlib.resources if pkg_resources is not available
        stream = (files(package) / resource_name).open('rb')

    try:
        yield stream
    finally:
        stream.close()


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
    if USE_PKG_RESOURCES:
        # Use pkg_resources.resource_filename if available
        path = resource_filename(package, resource_name)
        yield path
    else:
        # Fallback to importlib.resources if pkg_resources is not available
        temp_dir = tempfile.mkdtemp()
        try:
            resource_path = files(package) / resource_name
            if resource_path.is_dir():
                # Copy directory content to temp_dir if resource is a directory
                shutil.copytree(resource_path, os.path.join(temp_dir, os.path.basename(resource_path)), dirs_exist_ok=True)
                yield os.path.join(temp_dir, os.path.basename(resource_path))
            else:
                # Copy file to temp_dir if resource is a file
                temp_path = os.path.join(temp_dir, os.path.basename(resource_name))
                shutil.copy2(resource_path, temp_path)
                yield temp_path
        finally:
            # Cleanup temporary directory
            shutil.rmtree(temp_dir)
