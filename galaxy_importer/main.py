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
from pprint import pprint
import sys

from . import collection


def main(args=None):
    logging.basicConfig(
        stream=sys.stdout,
        format='%(levelname)s: %(message)s',
        level=logging.INFO)
    args = parse_args(args)

    json_data = call_importer(filepath=args.filepath)

    if args.print_result:
        pprint(json.loads(json_data))

    write_output_file(json_data)


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Import collection and run linting')
    parser.add_argument(
        '-f', '--filepath',
        default=None,
        required=True,
        help='Artifact to import.')
    parser.add_argument(
        '--print_result',
        dest='print_result',
        action='store_true',
        help='Print importer result.')
    return parser.parse_args(args=args)


def call_importer(filepath):
    """Returns result of galaxy_importer import process.

    :param filepath: Artifact file to import.
    """
    json_data = collection.import_collection(filepath)
    data = json.loads(json_data)
    if data['result'] == 'completed':
        print('Importer processing completed successfully')
    else:
        print(f'Error during importer proccessing: {data["error"]}')
    return json_data


def write_output_file(json_data):
    with open('importer_result.json', 'w') as output_file:
        output_file.write(json_data)


if __name__ == '__main__':
    exit(main())
