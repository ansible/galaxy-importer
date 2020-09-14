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

import yaml

from yamllint.config import YamlLintConfig
from yamllint import linter


def safe_load_file(file_path):
    d = {}
    with open(file_path) as fp:
        d = yaml.safe_load(fp)
    return d or {}


def lint_file(file_path):
    with open(file_path) as fp:
        conf = YamlLintConfig('extends: default')
        return linter.run(fp, conf)
