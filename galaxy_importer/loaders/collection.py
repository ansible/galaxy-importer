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
import re

import ansible_builder.introspect

from galaxy_importer import exceptions as exc
from galaxy_importer.finder import ContentFinder, FileWalker
from galaxy_importer import loaders
from galaxy_importer import schema
from galaxy_importer.utils import markup as markup_utils
from galaxy_importer.utils import chksums
from galaxy_importer.utils import string_utils

default_logger = logging.getLogger(__name__)

DOCUMENTATION_DIR = "docs"


class CollectionLoader(object):
    """Loads collection and content info."""

    def __init__(self, path, filename, cfg=None, logger=None):
        self.log = logger or default_logger
        self.path = path
        self.filename = filename
        self.cfg = cfg

        self.content_objs = None
        self.metadata = None
        self.file_manifest_file = None
        self.docs_blob = None
        self.contents = None

    def load(self):
        # NOTE: If we knew the chksum for MANIFEST.json, we could check it here first
        self.manifest = self._load_manifest()

        self.metadata = self.manifest.collection_info

        # The default name for 'file_manifest_file' is FILES.json
        self.file_manifest_file = self.manifest.file_manifest_file

        # load data from FILES.json
        self.file_manifest = self._load_file_manifest(
            path_prefix=self.path, file_manifest_file=self.file_manifest_file
        )

        # check chksum for each file in FILES.json
        # Note: Will raise exceptions on file_manifest / FILES.json errors
        self._check_file_manifest(self.path, self.file_manifest, self.file_manifest_file.name)

        self._rename_extract_path()
        self._check_filename_matches_manifest()
        self._check_metadata_filepaths()

        self.doc_strings = {}
        if self.cfg.run_ansible_doc:
            self.doc_strings = loaders.DocStringLoader(
                path=self.path,
                fq_collection_name="{}.{}".format(self.metadata.namespace, self.metadata.name),
                logger=self.log,
                cfg=self.cfg,
            ).load()

        self.content_objs = list(self._load_contents())

        self.contents = self._build_contents_blob()
        self.docs_blob = self._build_docs_blob()
        self.requires_ansible = loaders.RuntimeFileLoader(self.path).get_requires_ansible()
        self._check_ansible_test_ignore_files()
        self._check_ee_yml_dep_files()

        return schema.ImportResult(
            metadata=self.metadata,
            docs_blob=self.docs_blob,
            contents=self.contents,
            requires_ansible=self.requires_ansible,
        )

    def _check_ansible_test_ignore_files(self):  # pragma: no cover
        """Log a warning when ansible test sanity ignore files are present.
        Method excluded from pytest coverage, test exist outside repo via iqe.
        """
        IGNORE_FILE_REGEXP = re.compile(r"^ignore-.+\.txt$")
        IGNORE_WARNING = (
            "Ignore files skip ansible-test sanity tests, "
            "found {file} with {line_count} statement(s)"
        )

        sanity_path = os.path.join(self.path, "tests", "sanity")
        if not os.path.exists(sanity_path):
            return

        listdir = os.listdir(sanity_path)
        for ignore_file in filter(IGNORE_FILE_REGEXP.match, listdir):
            with open(os.path.join(sanity_path, ignore_file), "r") as f:
                line_count = len(f.readlines())
            self.log.warning(IGNORE_WARNING.format(file=ignore_file, line_count=line_count))

    def _check_ee_yml_dep_files(self):  # pragma: no cover
        """Check for python deps file and system deps file if they are listed in
        meta/execution-environment.yml, and log if listed files are not found

        Method excluded from pytest coverage, test exist outside repo via iqe.
        """

        try:
            python_deps, system_deps = ansible_builder.introspect.process_collection(self.path)
        except FileNotFoundError as e:
            self.log.error(
                f"Error when checking meta/execution-environment.yml for dependency files: {e}"
            )

    def _load_manifest(self):
        manifest_file = os.path.join(self.path, "MANIFEST.json")
        if not os.path.exists(manifest_file):
            raise exc.ManifestNotFound("No manifest found in collection")

        default_logger.debug("manifest_file: %s", manifest_file)

        with open(manifest_file, "r") as f:
            try:
                data = schema.CollectionArtifactManifest.parse(f.read())
            except ValueError as e:
                raise exc.ManifestValidationError(str(e)) from e

            default_logger.debug("data: %s", data)
            default_logger.debug("data.file_manifest_file: %s", data.file_manifest_file)
            return data

    def _load_file_manifest(self, path_prefix, file_manifest_file):
        """Load CollectionArtifactFileManifest data from file_manifest_file

        Args:
            path_prefix (str): Any file path prefix we need to add to file paths in the
                CollectionArtifactFile artifact_file
            file_manifest_file (CollectionArtifactFile): object with info about the
                FILES.json in the artifact. The info includes the name, type, path,
                and chksum.

        Raises:
            ManifestValidationError: If there are any errors loading, parsing,
                deserializing, or validating the data in file_manifest_file

        Returns:
            CollectionArtifactFileManifest: The data from file_manifest_file

        """
        default_logger.debug("file_manifest_file: %s", file_manifest_file)

        chksums.check_artifact_file(path_prefix=path_prefix, artifact_file=file_manifest_file)

        files_manifest_file = os.path.join(path_prefix, file_manifest_file.name)
        default_logger.debug("files_manifest_file: %s", files_manifest_file)

        with open(files_manifest_file, "r") as f:
            try:
                file_manifest = schema.CollectionArtifactFileManifest.parse(f.read())
            except ValueError as e:
                raise exc.ManifestValidationError(str(e))

        return file_manifest

    def _check_file_manifest(self, path_prefix, file_manifest, file_manifest_name):
        """Check the file content described in file_manifest

        Check the chksums for files.
        Check for any missing files.
        Check for any missing dirs.

        Args:
            path_prefix (str): Any file path prefix we need to add to file paths in the
                CollectionArtifactFile artifact_file
            file_manifest (CollectionArtifactFileManifest): Object with list of
                CollectionArtifactFile items. The CollectionArtifactFile data
                is used to check and validate each file.
            file_manifest_name (str): The name of the file manifest (ie, "FILES.json")

        Raises:
            CollectionArtifactFileNotFound: If artifact_file is not found on the file system.
            CollectionArtifactFileChecksumError: If the sha256sum of the on disk
                artifact_file contents does not match artifact_file.chksum_sha256.

        Returns:
            bool: All the items in file_manifest were found and valid
        """

        for artifact_file in file_manifest.files:
            if artifact_file.ftype != "file":
                continue

            chksums.check_artifact_file(path_prefix=path_prefix, artifact_file=artifact_file)

        # check the extract archive for any extra files.
        filewalker = FileWalker(collection_path=path_prefix)
        prefix = path_prefix + "/"
        found_file_set = set([string_utils.removeprefix(fp, prefix) for fp in filewalker.walk()])

        file_manifest_file_set = set([artifact_file.name for artifact_file in file_manifest.files])
        # The artifact contains MANIFEST.json and FILES.JSON, but they aren't
        # in file list in FILES.json so add them so we match expected.
        file_manifest_file_set.add("MANIFEST.json")
        file_manifest_file_set.add(file_manifest_name)

        difference = sorted(list(found_file_set.difference(file_manifest_file_set)))

        if difference:
            err_msg = f"Files in the artifact but not the file manifest: {difference}"
            raise exc.FileNotInFileManifestError(unexpected_files=difference, msg=err_msg)

        return True

    def _rename_extract_path(self):
        old_ns_dir = os.path.dirname(self.path)
        ansible_collections_dir = os.path.dirname(old_ns_dir)
        new_ns_dir = os.path.join(ansible_collections_dir, self.metadata.namespace)
        os.rename(old_ns_dir, new_ns_dir)

        old_name_dir = os.path.join(new_ns_dir, os.path.basename(self.path))
        new_name_dir = os.path.join(new_ns_dir, self.metadata.name)
        os.rename(old_name_dir, new_name_dir)
        self.path = new_name_dir
        self.log.debug(f"Renamed extract dir to: {self.path}")

    def _check_filename_matches_manifest(self):
        if not self.filename:
            return
        for item in ["namespace", "name", "version"]:
            filename_item = getattr(self.filename, item, None)
            metadata_item = getattr(self.metadata, item, None)
            if not filename_item:
                continue
            if filename_item != metadata_item:
                raise exc.ManifestValidationError(
                    f'Filename {item} "{filename_item}" did not match metadata "{metadata_item}"'
                )

    def _load_contents(self):
        """Find and load data for each content inside the collection."""
        found_contents = ContentFinder().find_contents(self.path, self.log)
        for content_type, rel_path in found_contents:
            loader_cls = loaders.get_loader_cls(content_type)
            loader = loader_cls(
                content_type, rel_path, self.path, self.doc_strings, self.cfg, self.log
            )
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
            raise exc.ImporterError("No collection readme found")
        rendered_readme = schema.RenderedDocFile(
            name=readme.name, html=markup_utils.get_html(readme)
        )

        rendered_doc_files = []
        doc_files = markup_utils.get_doc_files(os.path.join(self.path, DOCUMENTATION_DIR))
        if doc_files:
            rendered_doc_files = [
                schema.RenderedDocFile(name=f.name, html=markup_utils.get_html(f))
                for f in doc_files
            ]

        return schema.DocsBlob(
            collection_readme=rendered_readme,
            documentation_files=rendered_doc_files,
            contents=contents,
        )

    def _check_metadata_filepaths(self):
        # NOTE: This may be redundant if _check_file_manifest() looks for missing files
        paths = []
        paths.append(os.path.join(self.path, self.metadata.readme))
        if self.metadata.license_file:
            paths.append(os.path.join(self.path, self.metadata.license_file))
        for path in paths:
            if not os.path.exists(path):
                raise exc.ManifestValidationError(f"Could not find file {os.path.basename(path)}")
