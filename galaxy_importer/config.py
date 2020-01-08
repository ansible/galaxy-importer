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


FILENAME = 'galaxy-importer.cfg'


class Config(object):
    """Configuration for galaxy-importer."""

    _shared_state = {'_is_loaded': False}
    DEFAULTS = {
        'log_debug_main': False,
        'run_ansible_test': False,
        'infra_pulp': False,
        'infra_osd': False,
    }

    def __init__(self):
        """Set class attrs to shared state and load config if not loaded."""
        self.__dict__ = self._shared_state
        if not self._is_loaded:
            self._is_loaded = True
            self._load_config()

    def _load_config(self):
        """Set config to defaults and update with any file config."""

        self._shared_state.update(self.DEFAULTS)

        file_path = None
        file_locs = [
            f'/etc/galaxy-importer/{FILENAME}',
            os.path.join(os.path.dirname(__file__), FILENAME),
        ]

        for f in file_locs:
            if os.path.isfile(f):
                file_path = f
                break

        if file_path:
            config_parser = configparser.ConfigParser()
            config_parser.read(file_path)
            if 'galaxy-importer' not in config_parser:
                return
            file_cfg = config_parser['galaxy-importer']
            for k, v in vars(self).items():
                setattr(self, k, file_cfg.getboolean(k, v))
