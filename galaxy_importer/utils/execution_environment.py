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

    if os.path.exists(ex_env_path):
        ex_env = _load_yaml(ex_env_path, logger)
    else:
        logger.info('No execution environment data found.')
        return ex_env

    if 'dependencies' in ex_env and 'galaxy' in ex_env['dependencies'] and os.path.exists(
        os.path.join(path, ex_env['dependencies']['galaxy'])
    ):
        logger.info('Linting collection dependencies')
        galaxy_contents = _load_yaml(
            os.path.join(path, ex_env['dependencies']['galaxy']),
            logger
        )
        logger.info('Loading collection dependencies')
        ex_env = _write_to_ee(ex_env, 'galaxy', galaxy_contents)
    else:
        logger.warning('Galaxy dependencies file not found')

    if 'dependencies' in ex_env and 'python' in ex_env['dependencies'] and os.path.exists(
        os.path.join(path, ex_env['dependencies']['python'])
    ):
        logger.info('Loading python dependencies')
        python_contents = _load_python(os.path.join(path, ex_env['dependencies']['python']))
        ex_env = _write_to_ee(ex_env, 'python', python_contents)
    else:
        logger.warning('Python dependencies file not found')

    if 'dependencies' in ex_env and 'system' in ex_env['dependencies'] and os.path.exists(
        os.path.join(path, ex_env['dependencies']['system'])
    ):
        logger.info('Loading system dependencies')
        system_contents = _load_list(os.path.join(path, ex_env['dependencies']['system']))
        ex_env = _write_to_ee(ex_env, 'system', system_contents)
    else:
        logger.warning('System dependencies file not found')

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
