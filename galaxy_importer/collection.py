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

from collections import namedtuple
import logging
import os
from pkg_resources import iter_entry_points
import tarfile
import tempfile

import attr

from galaxy_importer import exceptions as exc
from galaxy_importer.finder import ContentFinder
from galaxy_importer import loaders
from galaxy_importer import schema
from galaxy_importer.utils import markup as markup_utils


default_logger = logging.getLogger(__name__)

DOCUMENTATION_DIR = 'docs'

CollectionFilename = \
    namedtuple("CollectionFilename", ["namespace", "name", "version"])


def import_collection(file, filename=None, logger=None):
    logger = logger or default_logger
    return _import_collection(file, filename, logger)


def _import_collection(file, filename, logger):
    with tempfile.TemporaryDirectory() as extract_dir:
        with tarfile.open(fileobj=file, mode='r') as pkg_tar:
            pkg_tar.extractall(extract_dir)

        data = CollectionLoader(extract_dir, filename, logger=logger).load()

    _run_post_load_plugins(
        artifact_file=file,
        metadata=data.metadata,
        content_objs=None,
        logger=logger,
    )

    return attr.asdict(data)


class CollectionLoader(object):
    """Loads collection and content info."""

    def __init__(self, path, filename, logger=None):
        self.log = logger or default_logger
        self.path = path
        self.filename = filename

        self.content_objs = None
        self.metadata = None
        self.docs_blob = None
        self.contents = None

    def load(self):
        self._load_collection_manifest()
        self._check_filename_matches_manifest()
        self.content_objs = list(self._load_contents())

        self.contents = self._build_contents_blob()
        self.docs_blob = self._build_docs_blob()

        return schema.ImportResult(
            metadata=self.metadata,
            docs_blob=self.docs_blob,
            contents=self.contents,
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

    def _check_filename_matches_manifest(self):
        if not self.filename:
            return
        if self.filename.namespace != self.metadata.namespace \
                or self.filename.name != self.metadata.name:
            raise exc.ManifestValidationError(
                'Filename did not match metadata')
        if self.filename.version != self.metadata.version:
            raise exc.ManifestValidationError(
                'Filename version did not match metadata')

    def _load_contents(self):
        """Find and load data for each content inside the collection."""
        found_contents = ContentFinder().find_contents(self.path, self.log)
        for content_type, rel_path in found_contents:
            loader_cls = loaders.get_loader_cls(content_type)
            loader = loader_cls(content_type, rel_path, self.path, self.log)
            content_obj = loader.load()
            yield content_obj

    def _build_contents_blob(self):
        """Build importer result contents from Content objects."""
        return [
            schema.ResultContentItem(
                name=c.name,
                content_type=c.content_type.value,
                description=c.description,
            )
            for c in self.content_objs
        ]

    def _build_docs_blob(self):
        """Build importer result docs_blob from collection documentation."""
        contents = [
            schema.DocsBlobContentItem(
                content_name=c.name,
                content_type=c.content_type.value,
                doc_strings=c.doc_strings,
                readme_file=c.readme_file,
                readme_html=c.readme_html,
            )
            for c in self.content_objs
        ]

        readme = markup_utils.get_readme_doc_file(self.path)
        if not readme:
            raise exc.ImporterError('No collection readme found')
        rendered_readme = schema.RenderedDocFile(
            name=readme.name, html=markup_utils.get_html(readme))

        rendered_doc_files = []
        doc_files = markup_utils.get_doc_files(
            os.path.join(self.path, DOCUMENTATION_DIR))
        if doc_files:
            rendered_doc_files = [
                schema.RenderedDocFile(
                    name=f.name, html=markup_utils.get_html(f))
                for f in doc_files
            ]

        return schema.DocsBlob(
            collection_readme=rendered_readme,
            documentation_files=rendered_doc_files,
            contents=contents,
        )


def _run_post_load_plugins(artifact_file, metadata, content_objs, logger=None):
    for ep in iter_entry_points(group='galaxy_importer.post_load_plugin'):
        logger.debug(f'Running plugin: {ep.module_name}')
        found_plugin = ep.load()
        found_plugin(
            artifact_file=artifact_file,
            metadata=metadata,
            content_objs=None,
            logger=logger,
        )
