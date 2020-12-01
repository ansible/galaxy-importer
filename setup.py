import os
import setuptools

from galaxy_importer import __version__

version = os.environ.get("ALTERNATE_VERSION", __version__)

setuptools.setup(
    version=version,
)
