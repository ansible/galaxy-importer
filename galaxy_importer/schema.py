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

from . import constants
from .utils.spdx_licenses import is_valid_license_id

SHA1_LEN = 40


def convert_none_to_empty_dict(val):
    """Returns an empty dict if val is None."""

    # if val is not a dict or val 'None' return val
    # and let the validators raise errors later
    if val is None:
        return {}
    return val


_FILENAME_RE = re.compile(
    r'^(?P<namespace>\w+)-(?P<name>\w+)-'
    r'(?P<version>[0-9a-zA-Z.+-]+)\.tar\.gz$'
)


@attr.s(slots=True)
class CollectionFilename(object):

    namespace = attr.ib()
    name = attr.ib()
    version = attr.ib(converter=semantic_version.Version)

    def __str__(self):
        return f'{self.namespace}-{self.name}-{self.version}.tar.gz'

    @classmethod
    def parse(cls, filename):
        match = _FILENAME_RE.match(filename)
        if not match:
            raise ValueError(
                'Invalid filename. Expected: '
                '{namespace}-{name}-{version}.tar.gz'
            )

        return cls(**match.groupdict())

    @namespace.validator
    @name.validator
    def _validator(self, attribute, value):
        if not constants.NAME_REGEXP.match(value):
            raise ValueError(
                'Invalid {0}: {1!r}'.format(attribute.name, value)
            )


@attr.s(frozen=True)
class BaseCollectionInfo(object):
    """Represents collection_info metadata in collection manifest.

    Includes data validation expected when collection is built.
    """

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

    license_file = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))
    readme = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))

    dependencies = attr.ib(
        factory=dict,
        converter=convert_none_to_empty_dict,
        validator=attr.validators.instance_of(dict))

    @property
    def label(self):
        return f"{self.namespace}.{self.name}"

    @staticmethod
    def value_error(msg):
        raise ValueError(f"Invalid collection metadata. {msg}") from None

    @namespace.validator
    @name.validator
    @version.validator
    def _check_required(self, attribute, value):
        """Check that value is present."""
        if not value:
            self.value_error(f"'{attribute.name}' is required")

    @namespace.validator
    @name.validator
    def _check_name(self, attribute, value):
        """Check value against name regular expression."""
        if not re.match(constants.NAME_REGEXP, value):
            self.value_error(f"'{attribute.name}' has invalid format: {value}")

    @version.validator
    def _check_version_format(self, attribute, value):
        """Check that version is in semantic version format."""
        if not semantic_version.validate(value):
            self.value_error(
                "Expecting 'version' to be in semantic version "
                f"format, instead found '{value}'.")

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
        invalid_licenses = [id for id in value if not is_valid_license_id(id)]
        if invalid_licenses:
            self.value_error(
                "Expecting 'license' to be a list of valid SPDX license "
                "identifiers, instead found invalid license identifiers: '{}' "
                "in 'license' value {}. "
                "For more info, visit https://spdx.org"
                .format(', '.join(invalid_licenses), value))

    @dependencies.validator
    def _check_dependencies_format(self, attribute, dependencies):
        """Check type and format of dependencies collection and version."""
        for collection, version_spec in dependencies.items():
            if not isinstance(collection, str):
                self.value_error("Expecting depencency to be string")
            if not isinstance(version_spec, str):
                self.value_error("Expecting depencency version to be string")

            try:
                namespace, name = collection.split('.')
            except ValueError:
                self.value_error(f"Invalid dependency format: '{collection}'")

            for value in [namespace, name]:
                if not re.match(constants.NAME_REGEXP, value):
                    self.value_error(
                        f"Invalid dependency format: '{value}' "
                        f"in '{namespace}.{name}'")

            if namespace == self.namespace and name == self.name:
                self.value_error("Cannot have self dependency")

            try:
                semantic_version.Spec(version_spec)
            except ValueError:
                self.value_error(
                    "Dependency version spec range invalid: "
                    f"{collection} {version_spec}")

    @tags.validator
    def _check_tags(self, attribute, value):
        """Check value against tag regular expression."""
        for tag in value:
            # TODO update tag format once resolved
            # https://github.com/ansible/galaxy/issues/1563
            if not re.match(constants.TAG_REGEXP, tag):
                self.value_error(f"'tag' has invalid format: {tag}")

    def __attrs_post_init__(self):
        """Checks called post init validation."""
        self._check_license_or_license_file(self.license, self.license_file)

    def _check_license_or_license_file(self, license_ids, license_file):
        """Confirm presence of either license or license_file."""
        if license_ids or license_file:
            return
        self.value_error(
            "Valid values for 'license' or 'license_file' are required. "
            f"But 'license' ({license_ids}) and "
            f"'license_file' ({license_file}) were invalid.")


@attr.s(frozen=True)
class GalaxyCollectionInfo(BaseCollectionInfo):
    """Represents collection_info metadata in galaxy.

    Includes additional data validation that is specific to galaxy.
    """

    def get_json(self):
        return self.__dict__

    def _check_required(self, name):
        """Check that value is present."""
        if not getattr(self, name):
            self.value_error(f"'{name}' is required by galaxy")

    def _check_non_null_str(self, name):
        """Check that if value is present, it must be a string."""
        value = getattr(self, name)
        if value is not None and not isinstance(value, str):
            self.value_error(f"'{name}' must be a string")

    def _check_tags_count(self):
        """Checks tag count in metadata against max tags count constant."""
        tags = getattr(self, 'tags')
        if tags is not None and len(tags) > constants.MAX_TAGS_COUNT:
            self.value_error(
                f"Expecting no more than {constants.MAX_TAGS_COUNT} tags "
                "in metadata")

    def __attrs_post_init__(self):
        """Additional galaxy checks called post init."""
        super().__attrs_post_init__()
        self._check_required('readme')
        self._check_required('authors')
        self._check_tags_count()
        for field in [
                        'description',
                        'repository',
                        'documentation',
                        'homepage',
                        'issues',
                     ]:
            self._check_non_null_str(field)


@attr.s(frozen=True)
class CollectionArtifactManifest(object):
    """Represents collection manifest metadata."""

    collection_info = attr.ib(type=GalaxyCollectionInfo)
    format = attr.ib(default=1)
    file_manifest_file = attr.ib(factory=dict)

    @classmethod
    def parse(cls, data):
        meta = json.loads(data)
        col_info = meta.pop('collection_info', None)
        meta['collection_info'] = GalaxyCollectionInfo(**col_info)
        return cls(**meta)
