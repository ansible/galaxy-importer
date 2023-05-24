import attr

from galaxy_importer import config
from galaxy_importer import exceptions as exc
from galaxy_importer.loaders import LegacyRoleLoader


def import_legacy_role(dirname, namespace, logger=None, cfg=None):
    """Process import on legacy role directory.

    :param dirname: directory of role.
    :param namespace: explicitly provided namespace of role.
    :param logger: Optional logger instance.
    :param cfg: Optional config.

    :raises exc.ImporterError: On errors that fail the import process.

    :return: metadata of legacy role
    """

    if namespace is None:
        raise exc.ImporterError("Importing legacy role requires explicit namespace")
    if not cfg:
        config_data = config.ConfigFile.load()
        cfg = config.Config(config_data=config_data)
    return _import_legacy_role(dirname, namespace, logger, cfg)


def _import_legacy_role(dirname, namespace, logger, cfg):
    """Returns legacy role metadata."""

    data = LegacyRoleLoader(dirname, namespace, cfg, logger).load()
    return attr.asdict(data)
