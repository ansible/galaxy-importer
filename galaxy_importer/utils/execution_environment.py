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

import os
import re

from galaxy_importer.utils import yaml as yaml_utils


def process_execution_environment(path, logger):
    ex_env = {}
    ex_env_path = os.path.join(path, 'meta', 'execution-environment.yml')

    if os.path.exists(ex_env_path):
        ex_env = _load_yaml(ex_env_path, logger)
    else:
        logger.info('No execution environment data found.')
        return ex_env
    if 'dependencies' not in ex_env:
        logger.warning('No dependencies found')
        return ex_env

    python_exists = os.path.exists(os.path.join(path, ex_env['dependencies']['python']))
    system_exists = os.path.exists(os.path.join(path, ex_env['dependencies']['system']))

    if 'python' in ex_env['dependencies'] and python_exists:
        logger.info('Loading python dependencies')
        python_contents = _pip_file_data(os.path.join(path, ex_env['dependencies']['python']))
        ex_env = _write_to_ee(ex_env, 'python', python_contents)
    elif 'python' in ex_env['dependencies'] and not python_exists:
        logger.warning('Python dependencies file not found')

    if 'system' in ex_env['dependencies'] and system_exists:
        logger.info('Loading system dependencies')
        system_contents = _bindep_file_data(os.path.join(path, ex_env['dependencies']['system']))
        ex_env = _write_to_ee(ex_env, 'system', system_contents)
    elif 'system' in ex_env['dependencies'] and not system_exists:
        logger.warning('System dependencies file not found')

    return ex_env


def _bindep_file_data(path):
    with open(path, 'r') as f:
        sys_content = f.read()

    sys_lines = []
    for line in sys_content.split('\n'):
        if line_is_empty(line):
            continue
        sys_lines.append(line)

    return sys_lines


def _pip_file_data(path):
    with open(path, 'r') as f:
        pip_content = f.read()

    pip_lines = []
    for line in pip_content.split('\n'):
        if line_is_empty(line):
            continue
        if '#' in line:
            line = re.sub(r' *#.*\n?', '', line)
        if line.startswith('-r') or line.startswith('--requirement'):
            _, new_filename = line.split(None, 1)
            new_path = os.path.join(os.path.dirname(path or '.'), new_filename)
            pip_lines.extend(_pip_file_data(new_path))
        else:
            pip_lines.append(line.rstrip())

    return pip_lines


def _load_yaml(path, logger):
    linting_result = yaml_utils.lint_file(path)
    for line in linting_result:
        logger.warning(line)
    return yaml_utils.safe_load_file(path)


def _write_to_ee(ex_env, key_name, key_value):
    if 'dependencies' not in ex_env.keys():
        ex_env['dependencies'] = {}
    ex_env['dependencies'][key_name] = key_value
    return ex_env


def line_is_empty(line):
    return bool((not line.strip()) or line.startswith('#'))
