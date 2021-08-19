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


class ImporterError(Exception):
    """Base class for importer exceptions"""

    pass


class AnsibleTestError(ImporterError):
    """Exception when running ansible-test."""

    pass


class ManifestNotFound(ImporterError):
    pass


class ManifestValidationError(ImporterError):
    pass


class ManifestFileListValidationError(ImporterError):
    pass


class FileNotInFileManifestError(ImporterError):
    """Files found in the artifact archive which were not listed in the file manifest"""

    def __init__(self, unexpected_files=None, msg=None):
        msg = msg or "Unexpected files found in the artifact but not the file manifest"
        super().__init__(msg)
        self.unexpected_files = unexpected_files or []


class CollectionArtifactFileNotFound(ImporterError):
    """The file the CollectionArtifactFile represents was not found"""

    def __init__(self, missing_file=None, msg=None):
        msg = msg or "File was listed in the file manifest but it was not found"
        super().__init__(msg)
        self.missing_file = missing_file


class CollectionArtifactFileChecksumError(ImporterError):
    """The chksum of the file contents does not match chksum_sha256sum"""

    pass


class ContentFindError(ImporterError):
    pass


class ContentLoadError(ImporterError):
    pass


class ContentNameError(ImporterError):
    pass


class RuntimeFileError(ImporterError):
    pass
