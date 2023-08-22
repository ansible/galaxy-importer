# (c) 2012-2020, Ansible by Red Hat
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

import configparser
import os


FILENAME = "galaxy-importer.cfg"
FILE_LOCATIONS = [
    f"/etc/galaxy-importer/{FILENAME}",
    os.path.join(os.path.dirname(__file__), FILENAME),
]
IMPORTER_INI_SECTION = "galaxy-importer"


def parse_string_to_bool(val):
    if val is None:
        return val
    if val.lower() in ["yes", "1", "true"]:
        return True
    if val.lower() in ["no", "0", "false"]:
        return False
    return val


class Config(object):
    """Configuration for galaxy-importer."""

    DEFAULTS = {
        "ansible_local_tmp": "~/.ansible/tmp",
        "ansible_test_local_image": False,
        "check_required_tags": False,
        "infra_osd": False,
        "local_image_docker": False,
        "log_level_main": "INFO",
        "require_v1_or_greater": False,
        "run_ansible_doc": True,
        "run_ansible_lint": True,
        "offline_ansible_lint": True,
        "run_ansible_test": False,
        "run_flake8": False,
        "tmp_root_dir": None,
    }

    def __init__(self, config_data=None):
        """Set config values to default, updated with any passed config_data."""
        _data = {}
        _data.update(self.DEFAULTS)
        _data.update(config_data or {})
        self.__dict__.update(_data)

        # Allow environment overrides for testing
        for key in self.__dict__.keys():
            env_key = "GALAXY_IMPORTER_" + key.upper()
            if env_key in os.environ:
                self.__dict__[key] = parse_string_to_bool(os.environ[env_key])


class ConfigFile(object):
    """Load config from file and return dictionary."""

    @staticmethod
    def load():
        env_config = os.getenv("GALAXY_IMPORTER_CONFIG")
        if env_config:
            FILE_LOCATIONS.insert(0, env_config)
        config_parser_data = ConfigFile._load_file(FILE_LOCATIONS)
        return ConfigFile._to_dictionary(config_parser_data)

    @staticmethod
    def _load_file(file_locations):
        file_path = None
        for f in file_locations:
            if os.path.isfile(f):
                file_path = f
                break

        if file_path:
            config_parser = configparser.ConfigParser()
            config_parser.read(file_path)
            if IMPORTER_INI_SECTION not in config_parser:
                return {}
            return config_parser[IMPORTER_INI_SECTION]
        return {}

    @staticmethod
    def _to_dictionary(config_parser_data):
        """Turn from configparser object in to dictionary, with booleans."""
        config_data = {}
        for key in list(config_parser_data):
            try:
                config_data[key] = config_parser_data.getboolean(key)
            except ValueError:
                config_data[key] = config_parser_data.get(key)
        return config_data
