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

import json
import logging
import os
import tarfile
import tempfile

import attr
import semantic_version

from galaxy_importer import exceptions as exc
from galaxy_importer import schema


default_logger = logging.getLogger(__name__)

ALLOWED_TYPES = ['text/markdown', 'text/x-rst']
RESULT_COMPLETED = 'completed'
RESULT_FAILED = 'failed'


def import_collection(filepath, logger=None):
    logger = logger or default_logger
    try:
        return _import_collection(filepath, logger)
    except Exception as exc:
        import_result = schema.ImportResult(
            result=RESULT_FAILED,
            error=str(exc),
        )
        return json.dumps(attr.asdict(import_result))


def _import_collection(filepath, logger):
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

        self.metadata = None
        self.documentation = None
        self.quality_score = None
        self.contents = None

    def load(self):
        self._load_collection_manifest()
        self._check_filename_matches_manifest()

        import_result = schema.ImportResult(
            metadata=self.metadata,
            documentation=self.documentation,
            quality_score=self.quality_score,
            contents=self.contents,
            result=RESULT_COMPLETED,
            error=None,
        )
        return json.dumps(attr.asdict(import_result))

    def _load_collection_manifest(self):
        manifest_file = os.path.join(self.path, 'MANIFEST.json')
        if not os.path.exists(manifest_file):
            raise exc.ManifestNotFound('No manifest found in collection')

        with open(manifest_file, 'r') as f:
            try:
                data = schema.CollectionArtifactManifest.parse(f.read())
            except ValueError as e:
                raise exc.ManifestValidationError(str(e))
            self.metadata = data.collection_info

    def _check_filename_matches_manifest(self):
        f = schema.CollectionFilename.parse(self.filename)
        if (f.namespace != self.metadata.namespace or
                f.name != self.metadata.name):
            raise exc.ManifestValidationError(
                'Filename did not match metadata')
        if f.version != semantic_version.Version(self.metadata.version):
            raise exc.ManifestValidationError(
                'Filename version did not match metadata')
