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
import subprocess
import sys

from galaxy_importer import legacy_role

from pprint import pprint

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
log = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
log.addHandler(handler)


def test_import_legacy_role():
    url = "https://github.com/geerlingguy/ansible-role-docker"

    with tempfile.TemporaryDirectory() as tmp_role_root:
        dn = os.path.join(tmp_role_root, "geerlingguy")
        os.makedirs(dn)
        dst = os.path.join(tmp_role_root, "geerlingguy", "docker")
        subprocess.run(f"git clone {url} {dst}", shell=True, check=True)
        metadata = legacy_role.import_legacy_role(git_clone_path=dst, logger=log)
        metadata.pop("readme_html", None)
        pprint(metadata)
