# (c) 2012-2019, Ansible by Red Hat
#
# This file is part of Ansible Galaxy
#
# Ansible Galaxy is free software: you can redistribute it and/or modify
# it under the terms of the Apache License as published by
# the Apache Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Ansible Galaxy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Apache License for more details.
#
# You should have received a copy of the Apache License
# along with Galaxy.  If not, see <http://www.apache.org/licenses/>.

import os
import logging
import tarfile
import tempfile

from .schema import CollectionArtifactManifest
from . import exceptions as exc


default_logger = logging.getLogger(__name__)

ALLOWED_TYPES = ['text/markdown', 'text/x-rst']


def import_collection(filepath, logger=None):
    logger = logger or default_logger
    filename = os.path.basename(filepath)

    with tempfile.TemporaryDirectory() as extract_dir:
        with tarfile.open(filepath, 'r') as pkg_tar:
            pkg_tar.extractall(extract_dir)

        return CollectionLoader(extract_dir, filename, logger=logger).load()


class CollectionLoader(object):
    """Loads collection and content info."""

    def __init__(self, path, filename, logger=None):
        self.log = logger or default_logger
        self.path = path
        self.filename = filename

        self.collection_info = None
        self.contents = None
        self.readme = None

    def load(self):
        self._load_collection_manifest()

        # TEMP: Temporary output stub
        import json
        return json.dumps(self.collection_info.__dict__)

    def _load_collection_manifest(self):
        manifest_file = os.path.join(self.path, 'MANIFEST.json')
        if not os.path.exists(manifest_file):
            raise exc.ManifestNotFound('No manifest found in collection')

        with open(manifest_file, 'r') as f:
            try:
                meta = CollectionArtifactManifest.parse(f.read())
            except ValueError as e:
                raise exc.ManifestValidationError(str(e))
            self.collection_info = meta.collection_info
