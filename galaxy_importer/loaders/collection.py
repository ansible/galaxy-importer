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
import shutil
from subprocess import Popen, PIPE, TimeoutExpired


try:
    from ansible_builder import introspect
except ImportError:
    from ansible_builder._target_scripts import introspect

from galaxy_importer import exceptions as exc
from galaxy_importer.finder import ContentFinder, FileWalker
from galaxy_importer import constants
from galaxy_importer import loaders, file_parser, schema
from galaxy_importer.utils import markup as markup_utils
from galaxy_importer.utils import chksums
from galaxy_importer.utils import string_utils

default_logger = logging.getLogger(__name__)

DOCUMENTATION_DIR = "docs"


def make_exclusions(basepath):
    exclusions = []

    for root, dirnames, filenames in os.walk(basepath):
        if root != basepath:
            continue
        for dirname in dirnames:
            if dirname == "roles":
                continue
            if dirname == "sanity":
                continue

            if dirname == "tests":
                tests_dir = os.path.join(root, dirname)
                for tests_root, tests_dirnames, tests_filenames in os.walk(tests_dir):
                    if tests_root != tests_dir:
                        continue
                    for tests_dirname in tests_dirnames:
                        if tests_dirname != "sanity":
                            continue
                        dn = (
                            os.path.join(tests_root, tests_dirname).replace(basepath + "/", "")
                            + "/"
                        )
                        if dn not in exclusions:
                            exclusions.append(dn)

            dn = os.path.join(root, dirname + "/").replace(basepath + "/", "")
            if dn not in exclusions:
                exclusions.append(dn)

    return exclusions


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

        # build the collections path for lint's module resolution
        self.collections_path = self.path
        if not callable(self.path):
            if hasattr(self.path, "strpath"):
                paths = self.path.strpath.split(os.sep)
            else:
                paths = self.path.split(os.sep)
            if "ansible_collections" in paths:
                ix = paths.index("ansible_collections")
                self.collections_path = os.sep.join(paths[: ix + 1])

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
        self.requires_ansible = file_parser.RuntimeFileParser(self.path).get_requires_ansible()
        self._check_ee_yml_dep_files()
        self._check_collection_changelog()

        if self.cfg.run_ansible_lint:
            if self.cfg.ansible_lint_serialize:
                self._lint_collection_roles_individually()
            else:
                self._lint_collection()
        self._check_ansible_test_ignore_files()

        return schema.ImportResult(
            metadata=self.metadata,
            docs_blob=self.docs_blob,
            contents=self.contents,
            requires_ansible=self.requires_ansible,
        )

    def _process_lint_results(self, proc, outs, errs, timedout=False):
        # EXIT CODES ...
        #  0 all good
        #  2 lint found problems
        # -9 lint process timed out OR was killed

        for line in outs.splitlines():
            self.log.warning(line.strip())

        for line in errs.splitlines():
            if line.startswith(constants.ANSIBLE_LINT_ERROR_PREFIXES):
                self.log.warning(line.rstrip())

        # The prevous code tries to be intelligent about what to display or not display
        # but we have serious errors from lint that are hidden by that logic. We should
        # attempt to inform the users of these errors (especially tracebacks).
        if proc.returncode != 0 and errs and "Traceback (most recent call last):" in errs:
            self.log.error(errs)

        self.log.debug(f"\tansible-lint returncode:{proc.returncode} timedout:{timedout}")

    def _lint_collection(self):
        """Log ansible-lint output.

        ansible-lint stdout are linter violations, they are logged as warnings and errors,
        depending on the rule level.

        ansible-lint stderr includes info about vars, file discovery,
        summary of linter violations, config suggestions, and raised errors.
        Only raised errors are logged, they are logged as errors.
        """

        self.log.info("Linting collection via ansible-lint...")

        if not shutil.which("ansible-lint"):
            self.log.warning("ansible-lint not found, skipping lint of collection")
            return

        cmd = [
            "/usr/bin/env",
            f"ANSIBLE_COLLECTIONS_PATH={self.collections_path}",
            f"ANSIBLE_LOCAL_TEMP={self.cfg.ansible_local_tmp}",
            "ansible-lint",
            "--profile",
            "production",
            "--parseable",
            "--nocolor",
        ]
        if self.cfg.offline_ansible_lint:
            cmd.append("--offline")

        if self.cfg.ansible_lint_dynamic_exclusions:
            exclusions = make_exclusions(self.path)
        else:
            exclusions = ["tests/integration/", "tests/unit/"]

        for exclusion in exclusions:
            cmd.append("--exclude")
            cmd.append(exclusion)

        self.log.info("CMD: " + " ".join(cmd))
        proc = Popen(
            cmd,
            cwd=self.path,
            encoding="utf-8",
            stdout=PIPE,
            stderr=PIPE,
        )

        timedout = False
        try:
            outs, errs = proc.communicate(timeout=self.cfg.ansible_lint_timeout)
        except (
            TimeoutExpired
        ):  # pragma: no cover - a TimeoutExpired mock would apply to both calls to commnicate()
            timedout = True
            self.log.error("Timeout on call to ansible-lint")
            proc.kill()
            outs, errs = proc.communicate()

        self._process_lint_results(proc, outs, errs, timedout=timedout)

        self.log.info("...ansible-lint run complete")

    def _lint_collection_roles_individually(self):
        roles_path = os.path.join(self.path, "roles")
        if not os.path.exists(roles_path):
            self.log.info("No roles found, skipping ansible-lint")

        role_paths = []
        for root, dirnames, filenames in os.walk(roles_path):
            if root != roles_path:
                continue
            for dirname in dirnames:
                role_paths.append(os.path.join(root, dirname))

        role_paths = sorted(role_paths)
        for rp in role_paths:
            self._lint_collection_role(rp)

    def _lint_collection_role(self, path):
        """Log ansible-lint output.
        ansible-lint stdout are linter violations, they are logged as warnings.
        ansible-lint stderr includes info about vars, file discovery,
        summary of linter violations, config suggestions, and raised errors.
        Only raised errors are logged, they are logged as errors.
        """

        path_name = os.path.basename(path)
        self.log.info(f"Linting role {path_name} via ansible-lint...")

        if not shutil.which("ansible-lint"):
            self.log.warning("ansible-lint not found, skipping lint of role")
            return

        cmd = [
            "/usr/bin/env",
            f"ANSIBLE_LOCAL_TEMP={self.cfg.ansible_local_tmp}",
            f"ANSIBLE_COLLECTIONS_PATH={self.collections_path}",
            "ansible-lint",
            path,
            "--profile",
            "production",
            "--parseable",
            "--nocolor",
            "--skip-list",
            "metadata",
            "--project-dir",
            os.path.dirname(path),
        ]
        self.log.info("CMD: " + " ".join(cmd))
        proc = Popen(
            cmd,
            cwd=self.path,
            encoding="utf-8",
            stdout=PIPE,
            stderr=PIPE,
        )

        timedout = False
        try:
            outs, errs = proc.communicate(timeout=self.cfg.ansible_lint_timeout)
        except (
            TimeoutExpired
        ):  # pragma: no cover - a TimeoutExpired mock would apply to both calls to commnicate()
            timedout = True
            self.log.error("Timeout on call to ansible-lint")
            proc.kill()
            outs, errs = proc.communicate()

        self._process_lint_results(proc, outs, errs, timedout=timedout)

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

    def _check_collection_changelog(self):
        """Log an error when a CHANGELOG file is not present in the root of the collection."""
        changelog_rst_path = os.path.join(self.path, "CHANGELOG.rst")
        changelog_md_path = os.path.join(self.path, "CHANGELOG.md")
        changelog_yaml_path = os.path.join(self.path, "changelogs/changelog.yaml")

        if (
            not os.path.exists(changelog_rst_path)
            and not os.path.exists(changelog_md_path)
            and not os.path.exists(changelog_yaml_path)
        ):
            self.log.warning(
                "No changelog found. "
                "Add a CHANGELOG.rst, CHANGELOG.md, or changelogs/changelog.yaml file."
            )

    def _check_ee_yml_dep_files(self):  # pragma: no cover
        """Check for python deps file and system deps file if they are listed in
        meta/execution-environment.yml, and log if listed files are not found

        Method excluded from pytest coverage, test exist outside repo via iqe.
        """

        try:
            python_deps, system_deps = introspect.process_collection(self.path)
        except FileNotFoundError as e:
            self.log.warning(
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
