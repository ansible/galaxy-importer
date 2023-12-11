import logging
import os

from galaxy_importer import exceptions as exc
from galaxy_importer import __version__
from galaxy_importer.utils import markup

default_logger = logging.getLogger(__name__)


def convert_markdown(dirname, logger=None):
    """Convert README.md to html.

    NOTE: README.md must exist in dirname

    :param dirname: directory of role.
    :param logger: Optional logger instance.

    :raises exc.ImporterError: On errors that fail the import process.

    :return: html markup of supplied README.md file
    """
    logger = logger or default_logger
    logger.info(f"Converting markdown with galaxy-importer {__version__}")

    # Ensure that dirname exists.
    if not os.path.exists(dirname):
        raise exc.ImporterError(f"Path does not exist: {dirname}")

    return _convert_markdown(dirname, logger)


def _convert_markdown(dirname, logger):
    doc_file = markup.get_readme_doc_file(dirname)
    if not doc_file:
        raise exc.ImporterError(f"Path does not contain README.md: {dirname}")
    else:
        logger.info(f"Processing {dirname}{doc_file.name}")
    return {"html": markup.get_html(doc_file)}
