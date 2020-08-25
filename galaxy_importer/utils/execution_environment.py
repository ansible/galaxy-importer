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
import requirements

from galaxy_importer.utils import yaml as yaml_utils


def process_execution_environment(path, logger):
    ex_env = {}
    ex_env_path = os.path.join(path, 'meta', 'execution-environment.yml')
    ex_env_exists = os.path.exists(ex_env_path)

    if ex_env_exists:
        ex_env = _load_yaml(ex_env_path, logger)

    if 'dependencies' in ex_env.keys():
        system_path = os.path.join(path, ex_env['dependencies']['system'])
        galaxy_path = os.path.join(path, ex_env['dependencies']['galaxy'])
        python_path = os.path.join(path, ex_env['dependencies']['python'])
    else:
        system_path = os.path.join(path, 'bindep.txt')
        galaxy_path = os.path.join(path, 'requirements.yml')
        python_path = os.path.join(path, 'requirements.txt')

    if os.path.exists(galaxy_path):
        logger.info('Linting collection dependencies')
        galaxy_contents = _load_yaml(galaxy_path, logger)
        logger.info('Loading collection dependencies')
        ex_env = _write_to_ee(ex_env, 'galaxy', galaxy_contents)
    if os.path.exists(python_path):
        logger.info('Loading python dependencies')
        python_contents = _load_python(python_path)
        ex_env = _write_to_ee(ex_env, 'python', python_contents)
    if os.path.exists(system_path):
        logger.info('Loading system dependencies')
        system_contents = _load_list(system_path)
        ex_env = _write_to_ee(ex_env, 'system', system_contents)

    if 'dependencies' not in ex_env.keys():
        logger.info('No execution environment data found.')
    return ex_env


def _load_list(path):
    content = []
    with open(path) as f:
        for line in f.readlines():
            if line.rstrip() != '' and not line.startswith('#'):
                content.append(line.rstrip())
    return content


def _load_python(path):
    content = []
    with open(path, 'r') as f:
        for req in requirements.parse(f):
            content.append(f'{req.name}: {req.specs}')
    return content


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
