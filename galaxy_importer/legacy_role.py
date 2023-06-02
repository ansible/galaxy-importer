import attr
import logging

from galaxy_importer import config
from galaxy_importer.loaders import LegacyRoleLoader
from galaxy_importer import __version__

default_logger = logging.getLogger(__name__)


def import_legacy_role(dirname, namespace, cfg=None, logger=None):
    """Process import on legacy role directory.

    :param dirname: directory of role.
    :param namespace: namespace of role.
    :param cfg: Optional config.
    :param logger: Optional logger instance.

    :raises exc.ImporterError: On errors that fail the import process.

    :return: metadata of legacy role
    """

    logger = logger or default_logger
    logger.info(f"Importing with galaxy-importer {__version__}")

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
