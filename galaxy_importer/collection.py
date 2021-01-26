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
import subprocess
import tempfile

import attr
import requests

from galaxy_importer import config
from galaxy_importer import exceptions as exc
from galaxy_importer.finder import ContentFinder
from galaxy_importer import loaders
from galaxy_importer import schema
from galaxy_importer.ansible_test import runners
from galaxy_importer.utils import execution_environment as ee_utils
from galaxy_importer.utils import markup as markup_utils
from galaxy_importer import __version__


default_logger = logging.getLogger(__name__)

DOCUMENTATION_DIR = 'docs'

CollectionFilename = \
    namedtuple("CollectionFilename", ["namespace", "name", "version"])


def import_collection(file, filename=None, logger=None, cfg=None):
    """Process import on collection artifact file object.

    :raises exc.ImporterError: On errors that fail the import process.
    """
    logger.info(f'Importing with galaxy-importer {__version__}')
    if not cfg:
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
    logger = logger or default_logger
    return _import_collection(file, filename, logger, cfg)


def _import_collection(file, filename, logger, cfg):
    with tempfile.TemporaryDirectory(dir=cfg.tmp_root_dir) as tmp_dir:
        sub_path = 'ansible_collections/placeholder_namespace/placeholder_name'
        extract_dir = os.path.join(tmp_dir, sub_path)
        os.makedirs(extract_dir)

        filepath = file.name
        if hasattr(file, 'file'):
            # handle a wrapped file object to get absolute filepath
            filepath = str(file.file.file.name)

        if not os.path.exists(filepath):
            parameters = {'ResponseContentDisposition': 'attachment;filename=archive.tar.gz'}
            storage_archive_url = file.storage.url(file.name, parameters=parameters)
            filepath = _download_archive(storage_archive_url, tmp_dir)
        _extract_archive(tarfile_path=filepath, extract_dir=extract_dir)

        data = CollectionLoader(extract_dir, filename, cfg=cfg, logger=logger).load()
        logger.info('Collection loading complete')

        ansible_test_runner = runners.get_runner(cfg=cfg)
        if ansible_test_runner:
            ansible_test_runner(dir=tmp_dir, metadata=data.metadata,
                                file=file, filepath=filepath, logger=logger).run()

    _run_post_load_plugins(
        artifact_file=file,
        metadata=data.metadata,
        content_objs=None,
        logger=logger,
    )

    return attr.asdict(data)


def _download_archive(file_url, download_dir):
    filepath = os.path.join(download_dir, 'archive.tar.gz')
    r = requests.get(file_url)
    with open(filepath, 'wb') as fh:
        fh.write(r.content)
        fh.seek(0)
    return filepath


def _extract_archive(tarfile_path, extract_dir):
    try:
        _extract_tar_shell(tarfile_path=tarfile_path, extract_dir=extract_dir)
    except subprocess.SubprocessError as e:
        raise exc.ImporterError('Error in tar extract subprocess: '
                                f'{str(e)}, filepath={tarfile_path}, stderr={e.stderr}')
    except FileNotFoundError as e:
        raise exc.ImporterError('File not found in tar extract subprocess: '
                                f'{str(e)}, filepath={tarfile_path}')


def _extract_tar_shell(tarfile_path, extract_dir):
    cwd = os.path.dirname(os.path.abspath(tarfile_path))
    file_name = os.path.basename(tarfile_path)
    args = [
        'tar',
        f'--directory={extract_dir}',
        '-xf',
        file_name,
    ]
    subprocess.run(args, cwd=cwd, stderr=subprocess.PIPE, check=True)


class CollectionLoader(object):
    """Loads collection and content info."""

    def __init__(self, path, filename, cfg=None, logger=None):
        self.log = logger or default_logger
        self.path = path
        self.filename = filename
        self.cfg = cfg

        self.content_objs = None
        self.metadata = None
        self.docs_blob = None
        self.contents = None

    def load(self):
        self._load_collection_manifest()
        self._rename_extract_path()
        self._check_filename_matches_manifest()
        self._check_metadata_filepaths()

        self.doc_strings = {}
        if self.cfg.run_ansible_doc:
            self.doc_strings = loaders.DocStringLoader(
                path=self.path,
                fq_collection_name='{}.{}'.format(self.metadata.namespace, self.metadata.name),
                logger=self.log,
                cfg=self.cfg,
            ).load()

        self.content_objs = list(self._load_contents())

        self.contents = self._build_contents_blob()
        self.docs_blob = self._build_docs_blob()
        self.requires_ansible = loaders.RuntimeFileLoader(self.path).get_requires_ansible()

        return schema.ImportResult(
            metadata=self.metadata,
            docs_blob=self.docs_blob,
            contents=self.contents,
            requires_ansible=self.requires_ansible,
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

    def _rename_extract_path(self):
        old_ns_dir = os.path.dirname(self.path)
        ansible_collections_dir = os.path.dirname(old_ns_dir)
        new_ns_dir = os.path.join(ansible_collections_dir, self.metadata.namespace)
        os.rename(old_ns_dir, new_ns_dir)

        old_name_dir = os.path.join(new_ns_dir, os.path.basename(self.path))
        new_name_dir = os.path.join(new_ns_dir, self.metadata.name)
        os.rename(old_name_dir, new_name_dir)
        self.path = new_name_dir
        self.log.debug(f'Renamed extract dir to: {self.path}')

    def _check_filename_matches_manifest(self):
        if not self.filename:
            return
        for item in ['namespace', 'name', 'version']:
            filename_item = getattr(self.filename, item, None)
            metadata_item = getattr(self.metadata, item, None)
            if not filename_item:
                continue
            if filename_item != metadata_item:
                raise exc.ManifestValidationError(
                    f'Filename {item} "{filename_item}" did not match metadata "{metadata_item}"')

    def _load_contents(self):
        """Find and load data for each content inside the collection."""
        found_contents = ContentFinder().find_contents(self.path, self.log)
        for content_type, rel_path in found_contents:
            loader_cls = loaders.get_loader_cls(content_type)
            loader = loader_cls(
                content_type, rel_path, self.path, self.doc_strings, self.cfg, self.log)
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

        # return an empty DocsBlob if run_ansible_doc=False
        rendered_readme = schema.RenderedDocFile()
        docs_blob = schema.DocsBlob(
            collection_readme=rendered_readme,
            documentation_files=[],
            contents=[],
        )

        if not self.cfg.run_ansible_doc:
            return docs_blob

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

        execution_environment = ee_utils.process_execution_environment(self.path, self.log)

        return schema.DocsBlob(
            collection_readme=rendered_readme,
            documentation_files=rendered_doc_files,
            contents=contents,
            execution_environment=execution_environment,
        )

    def _check_metadata_filepaths(self):
        paths = []
        paths.append(os.path.join(self.path, self.metadata.readme))
        if self.metadata.license_file:
            paths.append(os.path.join(self.path, self.metadata.license_file))
        for path in paths:
            if not os.path.exists(path):
                raise exc.ManifestValidationError(
                    f'Could not find file {os.path.basename(path)}')


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
