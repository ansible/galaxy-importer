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

FILENAME_REGEXP = re.compile(
    r"^(?P<namespace>\w+)-(?P<name>\w+)-"
    r"(?P<version>[0-9a-zA-Z.+-]+)\.tar\.gz$"
)


def main(args=None):
    logging.basicConfig(
        stream=sys.stdout,
        format='%(levelname)s: %(message)s',
        level=logging.INFO)
    args = parse_args(args)

    data = call_importer(filepath=args.file)
    if not data:
        return

    if args.print_result:
        print(json.dumps(data, indent=4))

    write_output_file(data)


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


def call_importer(filepath):
    """Returns result of galaxy_importer import process.

    :param file: Artifact file to import.
    """
    match = FILENAME_REGEXP.match(os.path.basename(filepath))
    namespace, name, version = match.groups()
    filename = collection.CollectionFilename(namespace, name, version)

    with open(filepath, 'rb') as f:
        try:
            data = collection.import_collection(f, filename)
        except Exception:
            logging.error('Error during importer proccessing:', exc_info=True)
            return None

    logging.info('Importer processing completed successfully')
    return data


def write_output_file(data):
    with open('importer_result.json', 'w') as output_file:
        output_file.write(json.dumps(data, indent=4))


if __name__ == '__main__':
    exit(main())
