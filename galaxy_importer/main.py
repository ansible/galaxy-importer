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
import logging
import sys

from . import collection


def start_import(filepath):
    """Outputs result of galaxy_importer import process.

    :param filepath: Artifact file to import.
    """
    json_data = collection.import_collection(filepath)
    # TODO: make default output go to file
    print(json_data)


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Import collection and run linting')
    parser.add_argument(
        '-f', '--filepath', default=None, help='Artifact to import.')
    return parser.parse_args(args=args)


def main(args=None):
    logging.basicConfig(
        stream=sys.stdout,
        format='%(message)s',
        level=logging.INFO)
    args = parse_args(args)
    start_import(filepath=args.filepath)


if __name__ == '__main__':
    exit(main())
