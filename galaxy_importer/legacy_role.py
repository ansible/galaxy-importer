import attr
import logging
import os

from galaxy_importer import config
from galaxy_importer import exceptions as exc
from galaxy_importer.loaders import LegacyRoleLoader
from galaxy_importer import __version__

default_logger = logging.getLogger(__name__)


def import_legacy_role(dirname, namespace, cfg=None, logger=None):
    """Process import on legacy role directory.

    NOTE: Must be run inside the parent directory of the role (parent directory of dirname).

    :param dirname: directory of role.
    :param namespace: namespace of role.
    :param cfg: Optional config.
    :param logger: Optional logger instance.

    :raises exc.ImporterError: On errors that fail the import process.

    :return: metadata of legacy role
    """

    logger = logger or default_logger
    logger.info(f"Importing with galaxy-importer {__version__}")

    # Ensure that dirname exists.
    if not os.path.exists(dirname):
        raise exc.ImporterError(f"The path '{dirname}' does not exist")

    # Ensure the input dirname is a subdirectory of the current directory.
    if dirname == os.curdir:
        raise exc.ImporterError(
            "Cannot run importer from role directory. Switch to parent directory"
        )
    joined = os.path.join(os.curdir, os.path.basename(os.path.normpath(dirname)))
    if not os.path.exists(joined):
        raise exc.ImporterError("Must run importer from parent directory of legacy role")
    if not os.path.isdir(joined):
        raise exc.ImporterError("Legacy role must be a directory")

    # Load user-specified or default configuration.
    if cfg is None:
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)

    return _import_legacy_role(dirname, namespace, cfg, logger)


def _import_legacy_role(dirname, namespace, cfg, logger):
    """Returns legacy role metadata."""

    data = LegacyRoleLoader(dirname, namespace, cfg, logger).load()
    logger.info("Legacy role loading complete")
    return attr.asdict(data)
