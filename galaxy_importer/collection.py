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

import logging
import os
import tarfile
import tempfile

import attr

from galaxy_importer import exceptions as exc
from galaxy_importer.finder import ContentFinder
from galaxy_importer import loaders
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
        return attr.asdict(import_result)


def _import_collection(filepath, logger):
    with tempfile.TemporaryDirectory() as extract_dir:
        with tarfile.open(filepath, 'r') as pkg_tar:
            pkg_tar.extractall(extract_dir)

        data = CollectionLoader(extract_dir, filepath, logger=logger).load()

    return attr.asdict(data)


class CollectionLoader(object):
    """Loads collection and content info."""

    def __init__(self, path, filepath, logger=None):
        self.log = logger or default_logger
        self.path = path
        self.filepath = filepath

        self.content_objs = None
        self.metadata = None
        self.docs_blob = None
        self.contents = None

    def load(self):
        self._load_collection_manifest()
        # TODO(awcrosby): add filename check when worker can pass filename with
        # collection details instead of filename made of hash string
        self.content_objs = list(self._load_contents())

        # TEMP: logging contents
        self.log.debug(' ')
        for c in self.content_objs:
            self.log.debug(
                f'Loaded {c.content_type.value}: {c.name}, {c.description}')

        self.contents = self._build_contents_blob()
        self.docs_blob = self.build_docs_blob()

        return schema.ImportResult(
            metadata=self.metadata,
            docs_blob=self.docs_blob,
            contents=self.contents,
            result=RESULT_COMPLETED,
            error=None,
        )

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

    def _load_contents(self):
        """Find and load data for each content inside the collection."""
        found_contents = ContentFinder().find_contents(self.path, self.log)
        for content_type, rel_path in found_contents:
            loader_cls = loaders.get_loader_cls(content_type)
            loader = loader_cls(content_type, rel_path, self.path)
            content_obj = loader.load()
            yield content_obj

    def _build_contents_blob(self):
        """Build importer result contents from Content objects."""
        pass

    def build_docs_blob(self):
        """Build importer result docs_blob from collection documentation."""
        pass
