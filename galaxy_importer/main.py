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

import argparse
import json
import logging
import os
import re
import sys

from galaxy_importer import collection, legacy_role, markdown
from galaxy_importer import config
from galaxy_importer.exceptions import ImporterError

FILENAME_REGEXP = re.compile(
    r"^(?P<namespace>\w+)-(?P<name>\w+)-" r"(?P<version>[0-9a-zA-Z.+-]+)\.tar\.gz$"
)
logger = logging.getLogger(__name__)


def main(args=None):
    config_data = config.ConfigFile.load()
    cfg = config.Config(config_data=config_data)
    setup_logger(cfg)
    args = parse_args(args)

    data = call_importer(args, cfg=cfg)
    if not data:
        return 1

    if args.print_result:
        print(json.dumps(data, indent=4))

    write_output_file(data)


def setup_logger(cfg):
    """Sets up logger with custom formatter."""
    logger.setLevel(getattr(logging, cfg.log_level_main, "INFO"))

    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)


class CustomFormatter(logging.Formatter):
    """Formatter that does not display INFO loglevel."""

    def formatMessage(self, record):
        if record.levelno == logging.INFO:
            return "%(message)s" % vars(record)
        else:
            return "%(levelname)s: %(message)s" % vars(record)


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="Run importer on collection and save result to disk."
    )
    parser.add_argument("file", nargs="?", help="artifact to import")
    parser.add_argument(
        "--git-clone-path",
        dest="git_clone_path",
        help="git directory with collection that will get built",
    )
    parser.add_argument(
        "--output-path",
        dest="output_path",
        help="path where built collection will be stored",
    )
    parser.add_argument(
        "--print-result",
        dest="print_result",
        action="store_true",
        help="print importer result to console",
    )
    parser.add_argument(
        "--legacy-role",
        dest="legacy_role",
        action="store_true",
        help="import a legacy role rather than collection",
    )
    parser.add_argument(
        "--namespace", dest="namespace", help="namespace of the legacy role to import"
    )
    parser.add_argument(
        "--markdown",
        dest="markdown",
        action="store_true",
        help="returns html preview of README.md",
    )
    return parser.parse_args(args=args)


def call_importer(args, cfg):  # pragma: no cover
    """Returns result of galaxy_importer import process.

    :param file: Artifact file to import.

    Method excluded from pytest unit test coverage, tests exist in tests/integration
    """
    if args.legacy_role:
        if args.file is None:
            logger.error("Must supply the directory of the role")
            return None
        if args.namespace is None:
            logger.error("Importing legacy role requires explicit namespace")
            return None
        try:
            data = legacy_role.import_legacy_role(args.file, args.namespace, logger=logger, cfg=cfg)
        except ImporterError as e:
            logger.error(f"The import failed for the following reason: {str(e)}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error occurred: {str(e)}")
            return None
    elif args.markdown:
        if args.file is None:
            logger.error("Must supply the directory of README.md")
            return None
        try:
            data = markdown.convert_markdown(args.file, logger=logger)
        except ImporterError as e:
            logger.error(f"The markdown conversion failed for the following reason: {str(e)}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error occurred: {str(e)}")
    else:
        if not args.file:
            return collection.import_collection(
                git_clone_path=os.path.abspath(args.git_clone_path),
                output_path=os.path.abspath(args.output_path),
                logger=logger,
                cfg=cfg,
            )

        match = FILENAME_REGEXP.match(os.path.basename(args.file))
        namespace, name, version = match.groups()
        filename = collection.CollectionFilename(namespace, name, version)

        with open(args.file, "rb") as fh:
            try:
                data = collection.import_collection(fh, filename, logger=logger, cfg=cfg)
            except ImporterError as e:
                logger.error(f"The import failed for the following reason: {str(e)}")
                return None
            except Exception as e:
                logger.exception(f"Unexpected error occurred: {str(e)}")
                return None

    logger.info("Importer processing completed successfully")
    return data


def write_output_file(data):
    with open("importer_result.json", "w") as output_file:
        output_file.write(json.dumps(data, indent=4))


if __name__ == "__main__":
    exit(main())
