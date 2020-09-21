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

import ansible_builder.introspect


def process_execution_environment(path, logger):
    deps = ansible_builder.introspect.process_collection(path)
    ex_env = {}

    if len(deps[0]) == 0 and len(deps[1]) == 0:
        logger.info('No execution environment dependencies found')
        return ex_env

    if len(deps[0]) > 0:
        logger.info('Loading python dependencies')
        ex_env = _write_to_ee(ex_env, 'python', deps[0])

    if len(deps[1]) > 0:
        logger.info('Loading system dependencies')
        ex_env = _write_to_ee(ex_env, 'system', deps[1])

    return ex_env


def _write_to_ee(ex_env, key_name, key_value):
    if 'dependencies' not in ex_env.keys() or not ex_env['dependencies']:
        ex_env['dependencies'] = {}
    ex_env['dependencies'][key_name] = key_value
    return ex_env
