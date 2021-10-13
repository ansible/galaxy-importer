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
import subprocess
import tempfile

import attr
import requests

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

    :param file: file handle of type BufferedReader.  # TODO: confirm same w/ pulp-ans caller
    :param filename: namedtuple of CollectionFilename.  # TODO: confirm same w/ pulp-ans caller
    :param file_url: .  # TODO: confirm w/ pulp-ans caller
    :param git_clone_path: path to collection repo dir.  # TODO: should this just be dir to make generic?
    :param output_path: path where collection build tarball file will be written
    :param logger: Optional logger instance.
    :param cfg: Optional config.

    :raises exc.ImporterError: On errors that fail the import process.

    :return: metadata if `file`  provided, (metadata, file) if `git_clone_path` provided
    """
    logger.info(f"Importing with galaxy-importer {__version__}")
    if not cfg:
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
    logger = logger or default_logger

    if (file and git_clone_path) or not (file or git_clone_path):
        raise exc.ImporterError(
            "Expected either 'file' or 'git_clone_path' to be populated"
        )

    if git_clone_path:
        with tempfile.TemporaryDirectory(dir=cfg.tmp_root_dir) as tmp_dir:
            filepath, filename = _build_collection(git_clone_path, tmp_dir, logger)
            with open(filepath, "rb") as fh:
                metadata = _import_collection(fh, filename, file_url, logger, cfg)
            return (metadata, filepath)
            # TODO: switch to using output_path instead of tmp_dir

    return _import_collection(file, filename, file_url, logger, cfg)


def sync_collection(git_clone_path=None, logger=None, cfg=None):
    """Process collection metadata without linting to support pulp-ansible sync.

    Call _import_collection() with an overridden config to
    process metadata without linting and without running ansible-test.
    """

    logger = logger or default_logger
    if not cfg:
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
    logger.info(f"cfg={cfg}")

    # TODO: override cfg so ansible_test does not run

    file, filename = _build_collection(git_clone_path, logger)
    metadata = _import_collection(file, filename, file_url=None, logger=logger, cfg=cfg)
    return (metadata, file)
    # TODO: accept user param ouput_path


def _build_collection(git_clone_path, output_path, logger=None):
    """Runs `ansible-galaxy collection build` and returns file obj and filename."""

    logger = logger or default_logger
    logger.info("Building collection tarball with ansible-galaxy collection build")

    cmd = [
        "ansible-galaxy",
        "collection",
        "build",
        "--output-path",
        output_path
    ]
    result = subprocess.run(cmd, cwd=git_clone_path, capture_output=True)
    filename = os.listdir(output_path)[0]  # FIXME: get end of stdout, ideally regex then combine with output path
    file = os.path.join(output_path, filename)

    # TODO: switch to using user param output_path, use result.stdout to get collection build filename
    # TODO: raise ImporterError on result.returncode != 0

    return (file, filename)


def _import_collection(file, filename, file_url, logger, cfg):
    """Returns collection version metadata."""
    logger.info(f"type(file)={type(file)}")
    logger.info(f"type(filename)={type(filename)}")

    with tempfile.TemporaryDirectory(dir=cfg.tmp_root_dir) as tmp_dir:
        sub_path = "ansible_collections/placeholder_namespace/placeholder_name"
        extract_dir = os.path.join(tmp_dir, sub_path)
        os.makedirs(extract_dir)

        filepath = file.name
        if hasattr(file, "file"):
            # handle a wrapped file object to get absolute filepath
            filepath = str(file.file.file.name)

        if not os.path.exists(filepath):
            if not file_url:
                # TODO(awcrosby): remove after using https://pulp.plan.io/issues/8486
                parameters = {
                    "ResponseContentDisposition": "attachment;filename=archive.tar.gz"
                }
                file_url = file.storage.url(file.name, parameters=parameters)
            filepath = _download_archive(file_url, tmp_dir)

        _extract_archive(tarfile_path=filepath, extract_dir=extract_dir)

        data = CollectionLoader(extract_dir, filename, cfg=cfg, logger=logger).load()
        logger.info("Collection loading complete")

        ansible_test_runner = runners.get_runner(cfg=cfg)
        if ansible_test_runner:
            ansible_test_runner(
                dir=tmp_dir,
                metadata=data.metadata,
                file=file,
                filepath=filepath,
                logger=logger,
            ).run()

    return attr.asdict(data)


def _download_archive(file_url, download_dir):
    filepath = os.path.join(download_dir, "archive.tar.gz")
    r = requests.get(file_url)
    with open(filepath, "wb") as fh:
        fh.write(r.content)
        fh.seek(0)
    return filepath


def _extract_archive(tarfile_path, extract_dir):
    try:
        _extract_tar_shell(tarfile_path=tarfile_path, extract_dir=extract_dir)
    except subprocess.SubprocessError as e:
        raise exc.ImporterError(
            f"Error in tar extract subprocess: {str(e)}, filepath={tarfile_path}, stderr={e.stderr}"
        )
    except FileNotFoundError as e:
        raise exc.ImporterError(
            f"File not found in tar extract subprocess: {str(e)}, filepath={tarfile_path}"
        )


def _extract_tar_shell(tarfile_path, extract_dir):
    cwd = os.path.dirname(os.path.abspath(tarfile_path))
    file_name = os.path.basename(tarfile_path)
    args = [
        "tar",
        f"--directory={extract_dir}",
        "-xf",
        file_name,
    ]
    subprocess.run(args, cwd=cwd, stderr=subprocess.PIPE, check=True)
