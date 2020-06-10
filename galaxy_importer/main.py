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

from galaxy_importer import collection
from galaxy_importer import config
from galaxy_importer.exceptions import ImporterError

FILENAME_REGEXP = re.compile(
    r"^(?P<namespace>\w+)-(?P<name>\w+)-"
    r"(?P<version>[0-9a-zA-Z.+-]+)\.tar\.gz$"
)


def main(args=None):
    config_data = config.ConfigFile.load()
    cfg = config.Config(config_data=config_data)
    setup_logger(cfg)
    args = parse_args(args)

    data = call_importer(filepath=args.file, cfg=cfg)
    if not data:
        return 1

    if args.print_result:
        print(json.dumps(data, indent=4))

    write_output_file(data)


def setup_logger(cfg):
    """Sets up logger with custom formatter."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, cfg.log_level_main, 'INFO'))

    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)


class CustomFormatter(logging.Formatter):
    """Formatter that does not display INFO loglevel."""
    def formatMessage(self, record):
        if record.levelno == logging.INFO:
            return '%(message)s' % vars(record)
        else:
            return '%(levelname)s: %(message)s' % vars(record)


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Run importer on collection and save result to disk.')
    parser.add_argument(
        'file',
        help='artifact to import')
    parser.add_argument(
        '--print-result',
        dest='print_result',
        action='store_true',
        help='print importer result to console')
    return parser.parse_args(args=args)


def call_importer(filepath, cfg):
    """Returns result of galaxy_importer import process.

    :param file: Artifact file to import.
    """
    match = FILENAME_REGEXP.match(os.path.basename(filepath))
    namespace, name, version = match.groups()
    filename = collection.CollectionFilename(namespace, name, version)

    with open(filepath, 'rb') as f:
        try:
            data = collection.import_collection(f, filename, cfg=cfg)
        except ImporterError as e:
            logging.error(f'The import failed for the following reason: {str(e)}')
            return None
        except Exception:
            logging.error('Unexpected error occurred:', exc_info=True)
            return None

    logging.info('Importer processing completed successfully')
    return data


def write_output_file(data):
    with open('importer_result.json', 'w') as output_file:
        output_file.write(json.dumps(data, indent=4))


if __name__ == '__main__':
    exit(main())
