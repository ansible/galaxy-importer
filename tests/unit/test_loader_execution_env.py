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

import logging
import os
import tempfile

from galaxy_importer import loaders
from galaxy_importer.utils import execution_environment as ee_utils


REQUIREMENTS_TXT = """
google-auth>=1.0.1  # Apache-2.0
requests # Apache-2.0
requests-oauthlib # ISC
"""

BINDEP_TXT = """
# This is a cross-platform list tracking distribution packages needed by tests;
# see https://docs.openstack.org/infra/bindep/ for additional information.

libffi-devel [platform:rpm]
python3-devel [compile test platform:rpm]
"""

RESULT = {
    'dependencies': {
        'python': [
            'google-auth>=1.0.1  # Apache-2.0',
            'requests # Apache-2.0',
            'requests-oauthlib # ISC'
        ],
        'system': [
            'libffi-devel [platform:rpm]',
            'python3-devel [compile test platform:rpm]'
        ]
    }
}


def test_no_execution_env_data(tmpdir):
    loader = loaders.ExecutionEnvironmentLoader(collection_path=tmpdir, log=logging)
    assert loader.data is None


def test_no_directory():
    loader = loaders.ExecutionEnvironmentLoader(collection_path="/does/not/exist/", log=logging)
    assert loader.data is None


def test_execution_env_data():
    with tempfile.TemporaryDirectory() as dir:
        files = [
            os.path.join(dir, 'requirements.txt'),
            os.path.join(dir, 'bindep.txt')
        ]
        file_contents = [REQUIREMENTS_TXT, BINDEP_TXT]
        for f, c in zip(files, file_contents):
            with open(f, 'w') as fp:
                fp.write(c)
                fp.flush()
        assert RESULT == ee_utils.process_execution_environment(dir, logging)
