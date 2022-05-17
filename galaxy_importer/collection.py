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
import shutil
import subprocess
import tarfile
import tempfile

import attr

from galaxy_importer import config
from galaxy_importer import exceptions as exc
from galaxy_importer.loaders import CollectionLoader
from galaxy_importer.ansible_test import runners
from galaxy_importer import __version__

default_logger = logging.getLogger(__name__)

CollectionFilename = namedtuple("CollectionFilename", ["namespace", "name", "version"])


def import_collection(
    file=None,
    filename=None,
    file_url=None,
    git_clone_path=None,
    output_path=None,
    logger=None,
    cfg=None,
):
    """Process import on collection artifact file object.

    :param file: file handle of collection artifact.
    :param filename: namedtuple of CollectionFilename.
    :param file_url: storage url of collection artifact.
    :param git_clone_path: path to git repo directory of collection pre artifact build.
    :param output_path: path where collection build tarball file will be written.
    :param logger: Optional logger instance.
    :param cfg: Optional config.

    :raises exc.ImporterError: On errors that fail the import process.

    :return: metadata if `file`  provided, (metadata, filepath) if `git_clone_path` provided
    """

    logger = logger or default_logger
    logger.info(f"Importing with galaxy-importer {__version__}")
    if not cfg:
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)

    if (file and git_clone_path) or not (file or git_clone_path):
        raise exc.ImporterError("Expected either 'file' or 'git_clone_path' to be populated")

    if git_clone_path:
        filepath = _build_collection(git_clone_path, output_path, logger)
        with open(filepath, "rb") as fh:
            metadata = _import_collection(fh, filename=None, file_url=None, logger=logger, cfg=cfg)
        return (metadata, filepath)

    return _import_collection(file, filename, file_url, logger, cfg)


def sync_collection(git_clone_path, output_path, logger=None, cfg=None):
    """Process collection metadata without linting to support pulp-ansible sync.

    Call _import_collection() with an overridden config to
    process metadata without linting and without running ansible-test.
    """

    logger = logger or default_logger
    if not cfg:
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)

    cfg.run_ansible_test = False
    cfg.run_ansible_lint = False
    cfg.run_flake8 = False

    filepath = _build_collection(git_clone_path, output_path, logger)
    with open(filepath, "rb") as fh:
        metadata = _import_collection(fh, filename=None, file_url=None, logger=logger, cfg=cfg)
    return (metadata, filepath)


def _build_collection(git_clone_path, output_path, logger=None):
    """Runs `ansible-galaxy collection build` and returns artifact filepath."""

    logger = logger or default_logger
    logger.info("Building collection tarball with ansible-galaxy collection build")

    cmd = ["ansible-galaxy", "collection", "build", "--output-path", output_path]
    result = subprocess.run(cmd, cwd=git_clone_path, capture_output=True)

    if result.returncode != 0:
        raise exc.ImporterError(
            "Error running `ansible-galaxy collection build`: {}".format(
                result.stderr.decode("utf-8").rstrip()
            )
        )

    # TODO: use regex to get filename from stdout, compine with output_path in case cli output
    # ever changes from: Created collection for <namespace>.<name> at /<path>/<artifact>.tar.gz
    stdout = result.stdout.decode("utf-8").rstrip()
    filepath = stdout.split(" ")[-1]
    return filepath


def _import_collection(file, filename, file_url, logger, cfg):
    """Returns collection version metadata."""

    with tempfile.TemporaryDirectory(dir=cfg.tmp_root_dir) as tmp_dir:
        sub_path = "ansible_collections/placeholder_namespace/placeholder_name"
        extract_dir = os.path.join(tmp_dir, sub_path)
        os.makedirs(extract_dir)
        _extract_archive(fileobj=file, extract_dir=extract_dir)

        data = CollectionLoader(extract_dir, filename, cfg=cfg, logger=logger).load()
        logger.info("Collection loading complete")

        ansible_test_runner = runners.get_runner(cfg=cfg)
        if ansible_test_runner:
            filepath = file.name
            if not os.path.exists(filepath):
                filepath = os.path.join(tmp_dir, "archive.tar.gz")
                file.seek(0)
                with open(filepath, "wb") as newfile:
                    shutil.copyfileobj(file, newfile)

            file.seek(0)
            ansible_test_runner(
                dir=tmp_dir,
                metadata=data.metadata,
                file=file,
                filepath=filepath,
                file_url=file_url,
                logger=logger,
            ).run()

    return attr.asdict(data)


def _extract_archive(fileobj, extract_dir):
    fileobj.seek(0)
    with tarfile.open(fileobj=fileobj, mode="r") as tf:
        if any((item.startswith("/") or item.startswith("../")) for item in tf.getnames()):
            raise exc.ImporterError("Invalid file paths detected.")
        tf.extractall(extract_dir)
