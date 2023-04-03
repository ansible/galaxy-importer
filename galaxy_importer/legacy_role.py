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

from galaxy_importer import config
from galaxy_importer import exceptions as exc
from galaxy_importer.constants import ContentType
from galaxy_importer.loaders.legacy_role import LegacyRoleLoader
from galaxy_importer import __version__

default_logger = logging.getLogger(__name__)


def import_legacy_role(
    git_clone_path=None,
    logger=None,
    cfg=None,
):
    """Process import on legacy role clone path.

    :param git_clone_path: path to git repo directory of collection pre artifact build.
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

    if not git_clone_path:
        raise exc.ImporterError("Expected 'git_clone_path' to be populated")

    return _import_legacy_role(git_clone_path, logger=logger, cfg=cfg)


def _import_legacy_role(git_clone_path, logger, cfg):
    """Returns legacy role metadata."""

    data = LegacyRoleLoader(
        ContentType.ROLE,
        git_clone_path,
        git_clone_path,
        cfg=cfg,
        logger=logger
    ).load()
    logger.info("Role loading complete")

    return data
