# (c) 2012-2023, Ansible by Red Hat
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
import shutil
import tarfile
import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch

from galaxy_importer.collection import _extract_archive
from galaxy_importer.exceptions import ImporterError


class TestCollectionExtractArchive(unittest.TestCase):
    def test_valid_archive(self):
        # Create a valid tar archive with no invalid paths
        archive_data = b"testfile content"
        archive_file = BytesIO()
        with tarfile.open(fileobj=archive_file, mode="w") as tf:
            tarinfo = tarfile.TarInfo("testfile")
            tarinfo.size = len(archive_data)
            tf.addfile(tarinfo, BytesIO(archive_data))
        archive_file.seek(0)

        # Create a temporary extraction directory
        extract_dir = tempfile.mkdtemp(prefix="collection-archive-extract-test-")
        os.makedirs(extract_dir, exist_ok=True)

        try:
            # Test extracting the archive
            _extract_archive(archive_file, extract_dir)
        finally:
            pass

        # Assert that the extracted file exists
        extracted_file_path = os.path.join(extract_dir, "testfile")
        self.assertTrue(os.path.isfile(extracted_file_path))

        # Clean up the temporary extraction directory
        shutil.rmtree(extract_dir)

    def test_invalid_path_with_absolute_path(self):
        # Create an archive with invalid paths
        archive_data = b"testfile content"
        archive_file = BytesIO()
        with tarfile.open(fileobj=archive_file, mode="w") as tf:
            tarinfo = tarfile.TarInfo("/invalid_path")
            tarinfo.size = len(archive_data)
            tf.addfile(tarinfo, BytesIO(archive_data))
        archive_file.seek(0)

        # Create a temporary extraction directory
        extract_dir = tempfile.mkdtemp(prefix="collection-archive-extract-test-")
        os.makedirs(extract_dir, exist_ok=True)

        # Test extracting the archive with invalid paths
        with self.assertRaises(ImporterError):
            _extract_archive(archive_file, extract_dir)

        # Clean up the temporary extraction directory
        shutil.rmtree(extract_dir)

    def test_invalid_parent_reference(self):
        # Create an archive with invalid paths
        archive_data = b"testfile content"
        archive_file = BytesIO()
        with tarfile.open(fileobj=archive_file, mode="w") as tf:
            tarinfo = tarfile.TarInfo("../invalid_path")
            tarinfo.size = len(archive_data)
            tf.addfile(tarinfo, BytesIO(archive_data))
        archive_file.seek(0)

        # Create a temporary extraction directory
        extract_dir = tempfile.mkdtemp(prefix="collection-archive-extract-test-")
        os.makedirs(extract_dir, exist_ok=True)

        # Test extracting the archive with invalid paths
        with self.assertRaises(ImporterError):
            _extract_archive(archive_file, extract_dir)

        # Clean up the temporary extraction directory
        shutil.rmtree(extract_dir)

    def test_invalid_link_destination(self):
        # Create an archive with a link whose destination is "/"
        archive_data = b"testfile content"
        archive_file = BytesIO()
        with tarfile.open(fileobj=archive_file, mode="w") as tf:
            tarinfo = tarfile.TarInfo("testfile")
            tf.addfile(tarinfo, BytesIO(archive_data))
            tarinfo = tarfile.TarInfo("invalid_link")
            tarinfo.type = tarfile.SYMTYPE
            tarinfo.linkname = "/"
            tf.addfile(tarinfo)
        archive_file.seek(0)

        # Create a temporary extraction directory
        extract_dir = tempfile.mkdtemp(prefix="collection-archive-extract-test-")
        os.makedirs(extract_dir, exist_ok=True)

        # Test extracting the archive with an invalid link destination
        with self.assertRaises(ImporterError):
            _extract_archive(archive_file, extract_dir)

        # Clean up the temporary extraction directory
        os.rmdir(extract_dir)

    def test_valid_relative_symlink_in_subdir(self):
        # Relative symlinks with '..' that resolve within the extraction
        # directory should be allowed (e.g. collections like community-general
        # use these legitimately).
        archive_data = b"testfile content"
        archive_file = BytesIO()
        with tarfile.open(fileobj=archive_file, mode="w") as tf:
            tarinfo = tarfile.TarInfo(".")
            tarinfo.type = tarfile.DIRTYPE
            tarinfo.mode = 493
            tf.addfile(tarinfo, BytesIO(archive_data))
            tarinfo.name = "testdir1"
            tf.addfile(tarinfo, BytesIO(archive_data))
            tarinfo.name = "testdir2"
            tf.addfile(tarinfo, BytesIO(archive_data))
            tarinfo.name = "testdir2/link"
            tarinfo.type = tarfile.SYMTYPE
            tarinfo.mode = 511
            tarinfo.linkname = "../testdir1"
            tf.addfile(tarinfo, BytesIO(archive_data))
        archive_file.seek(0)

        extract_dir = tempfile.mkdtemp(prefix="collection-archive-extract-test-")
        os.makedirs(extract_dir, exist_ok=True)

        _extract_archive(archive_file, extract_dir)

        extracted_file_path = os.path.join(extract_dir, "testdir2/link")
        self.assertTrue(os.path.islink(extracted_file_path))

        shutil.rmtree(extract_dir)

    def test_symlink_traversal_outside_root_rejected(self):
        # Symlinks targeting paths outside the extraction root via '..'
        # must be rejected (CVE-2025-4138).
        archive_file = BytesIO()
        with tarfile.open(fileobj=archive_file, mode="w") as tf:
            tarinfo = tarfile.TarInfo("escape_link")
            tarinfo.type = tarfile.SYMTYPE
            tarinfo.linkname = "../../tmp"
            tf.addfile(tarinfo)
        archive_file.seek(0)

        extract_dir = tempfile.mkdtemp(prefix="collection-archive-extract-test-")
        os.makedirs(extract_dir, exist_ok=True)

        with self.assertRaises(ImporterError):
            _extract_archive(archive_file, extract_dir)

        shutil.rmtree(extract_dir)

    def test_valid_relative_symlink_without_traversal(self):
        # Relative symlinks that don't use '..' should still be allowed.
        archive_data = b"testfile content"
        archive_file = BytesIO()
        with tarfile.open(fileobj=archive_file, mode="w") as tf:
            tarinfo = tarfile.TarInfo("testdir")
            tarinfo.type = tarfile.DIRTYPE
            tarinfo.mode = 493
            tf.addfile(tarinfo)

            tarinfo = tarfile.TarInfo("testdir/realfile")
            tarinfo.size = len(archive_data)
            tf.addfile(tarinfo, BytesIO(archive_data))

            tarinfo = tarfile.TarInfo("testdir/link")
            tarinfo.type = tarfile.SYMTYPE
            tarinfo.linkname = "realfile"
            tf.addfile(tarinfo)
        archive_file.seek(0)

        extract_dir = tempfile.mkdtemp(prefix="collection-archive-extract-test-")
        os.makedirs(extract_dir, exist_ok=True)

        _extract_archive(archive_file, extract_dir)

        extracted_link = os.path.join(extract_dir, "testdir/link")
        self.assertTrue(os.path.islink(extracted_link))

        shutil.rmtree(extract_dir)

    @patch("galaxy_importer.collection.hasattr", side_effect=lambda obj, name: False)
    def test_valid_archive_without_data_filter(self, mock_hasattr):
        # Simulate older Python (< 3.12) where tarfile.data_filter doesn't exist.
        archive_data = b"testfile content"
        archive_file = BytesIO()
        with tarfile.open(fileobj=archive_file, mode="w") as tf:
            tarinfo = tarfile.TarInfo("testfile")
            tarinfo.size = len(archive_data)
            tf.addfile(tarinfo, BytesIO(archive_data))
        archive_file.seek(0)

        extract_dir = tempfile.mkdtemp(prefix="collection-archive-extract-test-")
        os.makedirs(extract_dir, exist_ok=True)

        _extract_archive(archive_file, extract_dir)

        extracted_file_path = os.path.join(extract_dir, "testfile")
        self.assertTrue(os.path.isfile(extracted_file_path))

        shutil.rmtree(extract_dir)
