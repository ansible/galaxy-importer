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
import re

import attr
import semantic_version

from galaxy_importer import config
from galaxy_importer import constants
from galaxy_importer.utils.spdx_licenses import is_valid_license_id

MAX_LENGTH_AUTHOR = 64
MAX_LENGTH_LICENSE = 32
MAX_LENGTH_NAME = 64
MAX_LENGTH_TAG = 64
MAX_LENGTH_URL = 2000
MAX_LENGTH_VERSION = 128

SHA1_LEN = 40
REQUIRED_TAG_LIST = [
    "application",
    "cloud",
    "database",
    "infrastructure",
    "linux",
    "monitoring",
    "networking",
    "security",
    "storage",
    "tools",
    "windows",
]


def convert_none_to_empty_dict(val):
    """Returns an empty dict if val is None."""

    # if val is not a dict or val 'None' return val
    # and let the validators raise errors later
    if val is None:
        return {}
    return val


_FILENAME_RE = re.compile(
    r"^(?P<namespace>\w+)-(?P<name>\w+)-" r"(?P<version>[0-9a-zA-Z.+-]+)\.tar\.gz$"
)


@attr.s(slots=True)
class CollectionFilename(object):

    namespace = attr.ib()
    name = attr.ib()
    version = attr.ib(converter=semantic_version.Version)

    def __str__(self):
        return f"{self.namespace}-{self.name}-{self.version}.tar.gz"

    @classmethod
    def parse(cls, filename):
        match = _FILENAME_RE.match(filename)
        if not match:
            raise ValueError("Invalid filename. Expected: {namespace}-{name}-{version}.tar.gz")

        return cls(**match.groupdict())

    @namespace.validator
    @name.validator
    def _validator(self, attribute, value):
        if not constants.NAME_REGEXP.match(value):
            raise ValueError("Invalid {0}: {1!r}".format(attribute.name, value))


@attr.s(frozen=True)
class CollectionInfo(object):
    """Represents collection_info metadata in collection manifest."""

    namespace = attr.ib(default=None)
    name = attr.ib(default=None)
    version = attr.ib(default=None)
    license = attr.ib(factory=list)
    description = attr.ib(default=None)

    repository = attr.ib(default=None)
    documentation = attr.ib(default=None)
    homepage = attr.ib(default=None)
    issues = attr.ib(default=None)

    authors = attr.ib(factory=list)
    tags = attr.ib(factory=list)

    license_file = attr.ib(default=None)
    readme = attr.ib(default=None)

    dependencies = attr.ib(
        factory=dict,
        converter=convert_none_to_empty_dict,
        validator=attr.validators.instance_of(dict),
    )

    @property
    def label(self):
        return f"{self.namespace}.{self.name}"

    @staticmethod
    def value_error(msg):
        raise ValueError(f"Invalid collection metadata. {msg}") from None

    @namespace.validator
    @name.validator
    @version.validator
    @readme.validator
    @authors.validator
    @repository.validator
    def _check_required(self, attribute, value):
        """Check that value is present."""
        if not value:
            self.value_error(f"'{attribute.name}' is required")

    @namespace.validator
    @name.validator
    def _check_name(self, attribute, value):
        """Check value against name regular expression and max length."""
        if not re.match(constants.NAME_REGEXP, value):
            self.value_error(f"'{attribute.name}' has invalid format: {value}")
        if len(value) > MAX_LENGTH_NAME:
            self.value_error(
                f"'{attribute.name}' must not be greater than {MAX_LENGTH_NAME} characters"
            )

    @version.validator
    def _check_version_format(self, attribute, value):
        """Check that version is in semantic version format, and max length."""
        if not semantic_version.validate(value):
            self.value_error(
                f"Expecting 'version' to be in semantic version format, instead found '{value}'."
            )
        if len(value) > MAX_LENGTH_VERSION:
            self.value_error(f"'version' must not be greater than {MAX_LENGTH_VERSION} characters")

        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        if cfg.require_v1_or_greater:
            if semantic_version.Version(value) < semantic_version.Version("1.0.0"):
                self.value_error("Config is enabled that requires version to be 1.0.0 or greater.")

    @authors.validator
    @tags.validator
    @license.validator
    def _check_list_of_str(self, attribute, value):
        """Check that value is a list of strings."""
        err_msg = "Expecting '{attr}' to be a list of strings"
        if not isinstance(value, list):
            self.value_error(err_msg.format(attr=attribute.name))
        for list_item in value:
            if not isinstance(list_item, str):
                self.value_error(err_msg.format(attr=attribute.name))

    @license.validator
    def _check_licenses(self, attribute, value):
        """Check that all licenses in license list are valid."""
        for license in value:
            if len(license) > MAX_LENGTH_LICENSE:
                self.value_error(
                    f"Each license in 'licenses' list must not be greater than "
                    f"{MAX_LENGTH_LICENSE} characters"
                )
        invalid_licenses = [id for id in value if not is_valid_license_id(id)]
        if invalid_licenses:
            self.value_error(
                "Expecting 'license' to be a list of valid SPDX license "
                "identifiers, instead found invalid license identifiers: '{}' "
                "in 'license' value {}. "
                "For more info, visit https://spdx.org".format(", ".join(invalid_licenses), value)
            )

    @dependencies.validator
    def _check_dependencies_format(self, attribute, dependencies):
        """Check type and format of dependencies collection and version."""
        for collection, version_spec in dependencies.items():
            if not isinstance(collection, str):
                self.value_error("Expecting depencency to be string")
            if not isinstance(version_spec, str):
                self.value_error("Expecting depencency version to be string")

            try:
                namespace, name = collection.split(".")
            except ValueError:
                self.value_error(f"Invalid dependency format: '{collection}'")

            for value in [namespace, name]:
                if not re.match(constants.NAME_REGEXP, value):
                    self.value_error(
                        f"Invalid dependency format: '{value}' in '{namespace}.{name}'"
                    )

            if namespace == self.namespace and name == self.name:
                self.value_error("Cannot have self dependency")

            try:
                semantic_version.SimpleSpec(version_spec)
            except ValueError:
                self.value_error(
                    f"Dependency version spec range invalid: {collection} {version_spec}"
                )

    @tags.validator
    def _check_tags(self, attribute, value):
        """Check tags field for
        - presense of at least one required tag based on config
        - maximum count of tags
        - tag regular expression
        - tag max length
        """
        no_req_tag_err = f'At least one tag required from tag list: {", ".join(REQUIRED_TAG_LIST)}'

        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
        if cfg.check_required_tags and not value:
            self.value_error(no_req_tag_err)

        if cfg.check_required_tags and (not any(tag in REQUIRED_TAG_LIST for tag in value)):
            self.value_error(no_req_tag_err)

        if not value:
            return

        if len(value) > constants.MAX_TAGS_COUNT:
            self.value_error(f"Expecting no more than {constants.MAX_TAGS_COUNT} tags in metadata")

        for tag in value:
            if not re.match(constants.NAME_REGEXP, tag):
                self.value_error(f"'tag' has invalid format: {tag}")
            if len(tag) > MAX_LENGTH_TAG:
                self.value_error(
                    f"Each tag in 'tags' list must not be greater than {MAX_LENGTH_TAG} characters"
                )

    @description.validator
    @repository.validator
    @documentation.validator
    @homepage.validator
    @issues.validator
    @license_file.validator
    @repository.validator
    def _check_non_null_str(self, attribute, value):
        """Check that if value is present, it must be a string."""
        if value is not None and not isinstance(value, str):
            self.value_error(f"'{attribute.name}' must be a string")

    @documentation.validator
    @homepage.validator
    @issues.validator
    @repository.validator
    def _check_max_length_url(self, attribute, value):
        """Check value is not greater than max length of url"""
        if not value:
            return
        if len(value) > MAX_LENGTH_URL:
            self.value_error(
                f"'{attribute.name}' must not be greater than {MAX_LENGTH_URL} characters"
            )

    @authors.validator
    def _check_max_length_author(self, attribute, value):
        """Check each value list item is not greater than max length of author"""
        for author in value:
            if len(author) > MAX_LENGTH_AUTHOR:
                self.value_error(
                    f"Each author in 'authors' list must not be greater than "
                    f"{MAX_LENGTH_AUTHOR} characters"
                )

    def __attrs_post_init__(self):
        """Checks called post init validation."""
        self._check_license_or_license_file()

    def _check_license_or_license_file(self):
        """Confirm mutually exclusive presence of license or license_file."""
        if bool(self.license) != bool(self.license_file):
            return

        if self.license and self.license_file:
            self.value_error("The 'license' and 'license_file' keys are mutually exclusive")

        self.value_error(
            "Valid values for 'license' or 'license_file' are required. "
            f"But 'license' ({self.license}) and 'license_file' ({self.license_file}) were invalid."
        )


@attr.s(frozen=True)
class CollectionArtifactFile(object):
    name = attr.ib()
    ftype = attr.ib()
    src_name = attr.ib(default=None)
    chksum_type = attr.ib(default="sha256")
    chksum_sha256 = attr.ib(default=None)
    format = attr.ib(default=1)


@attr.s(frozen=True)
class CollectionArtifactManifest(object):
    """Represents collection manifest metadata."""

    collection_info = attr.ib(type=CollectionInfo)
    format = attr.ib(default=1)

    file_manifest_file = attr.ib(
        default=None,
        type=CollectionArtifactFile,
        validator=attr.validators.optional(attr.validators.instance_of(CollectionArtifactFile)),
    )

    @classmethod
    def parse(cls, data):
        meta = json.loads(data)
        col_info = meta.pop("collection_info", None)
        meta["collection_info"] = CollectionInfo(**col_info)

        try:
            file_manifest_file = meta["file_manifest_file"]
        except KeyError as e:
            msg = "MANIFEST.json did not contain a 'file_manifest_file' item pointing to FILES.json"
            raise ValueError(msg) from e
        meta["file_manifest_file"] = CollectionArtifactFile(**file_manifest_file)
        return cls(**meta)


def convert_list_to_artifact_file_list(val):
    """Convert a list of dicts with file info into list of CollectionArtifactFile"""

    new_list = []
    for file_item in val:
        if isinstance(file_item, CollectionArtifactFile):
            new_list.append(file_item)
        else:
            artifact_file = CollectionArtifactFile(
                name=file_item["name"],
                ftype=file_item["ftype"],
                chksum_type=file_item.get("chksum_type"),
                chksum_sha256=file_item.get("chksum_sha256"),
            )
            new_list.append(artifact_file)

    return new_list


@attr.s(frozen=True)
class CollectionArtifactFileManifest(object):
    files = attr.ib(factory=list, converter=convert_list_to_artifact_file_list)

    format = attr.ib(default=1, validator=attr.validators.instance_of(int))

    @classmethod
    def parse(cls, data):
        artifact_file_manifest_data = json.loads(data)
        artifact_file_list = artifact_file_manifest_data["files"]
        return cls(files=artifact_file_list)


@attr.s(frozen=True)
class ResultContentItem(object):
    name = attr.ib()
    content_type = attr.ib()
    description = attr.ib()


@attr.s(frozen=True)
class ImportResult(object):
    """Result of the import process, collection metadata, and contents."""

    metadata = attr.ib(default=None, type=CollectionInfo)
    docs_blob = attr.ib(factory=dict)
    contents = attr.ib(factory=list, type=ResultContentItem)
    custom_license = attr.ib(default=None)
    requires_ansible = attr.ib(default=None)


@attr.s
class Content(object):
    """Represents content found in a collection."""

    name = attr.ib()
    content_type = attr.ib(type=constants.ContentType)
    doc_strings = attr.ib(factory=dict)
    description = attr.ib(default=None)
    readme_file = attr.ib(default=None)
    readme_html = attr.ib(default=None)

    def __attrs_post_init__(self):
        """Set description if a plugin has doc_strings populated."""
        if not self.doc_strings:
            return
        if not self.doc_strings.get("doc", None):
            return
        self.description = self.doc_strings["doc"].get("short_description", None)


@attr.s(frozen=True)
class RenderedDocFile(object):
    """Name and html of a documenation file, part of DocsBlob."""

    name = attr.ib(default=None)
    html = attr.ib(default=None)


@attr.s(frozen=True)
class DocsBlobContentItem(object):
    """Documenation for piece of content, part of DocsBlob."""

    content_name = attr.ib()
    content_type = attr.ib()
    doc_strings = attr.ib(factory=dict)
    readme_file = attr.ib(default=None)
    readme_html = attr.ib(default=None)


@attr.s(frozen=True)
class DocsBlob(object):
    """All documenation that is part of a collection."""

    collection_readme = attr.ib(type=RenderedDocFile)
    documentation_files = attr.ib(factory=list, type=RenderedDocFile)
    contents = attr.ib(factory=list, type=DocsBlobContentItem)
