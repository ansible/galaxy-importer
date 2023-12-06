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
        # Create a valid archive with a relative symlink in a subdir
        # and the target in the top dir
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

        # Create a temporary extraction directory
        extract_dir = tempfile.mkdtemp(prefix="collection-archive-extract-test-")
        os.makedirs(extract_dir, exist_ok=True)

        try:
            _extract_archive(archive_file, extract_dir)
        finally:
            pass

        extracted_file_path = os.path.join(extract_dir, "testdir2/link")
        self.assertTrue(os.path.islink(extracted_file_path))

        # Clean up the temporary extraction directory
        shutil.rmtree(extract_dir)
