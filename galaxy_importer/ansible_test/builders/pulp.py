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

import logging
import os
import pexpect
import requests
import socket
import subprocess
import time

default_logger = logging.getLogger(__name__)
API_CHECK_RETRIES = 300
API_CHECK_DELAY_SECONDS = 1


class PulpServer(object):
    """Deploy Pulp All in One image"""
    def __init__(self, logger):
        self.api_url = f'http://{socket.gethostname()}:8080'
        self.base_dir = f"/tmp/pulp/"
        self.content_url = f'http://{socket.gethostname()}:8081'
        self.log = logger or default_logger

    def start(self):
        """Start Pulp server""" 
        self.log.info("Starting Pulp server")
        settings_file = '/tmp/pulp/settings/settings.py'
        # TODO Reuse existing Pulp installation?
        if os.path.isfile(settings_file):
            self.cleanup()
        self._create_settings_dirs()
        self._add_settings()
        self._start_pulp()

    def get_api_url(self):
        return self.api_url

    def get_content_url(self):
        return self.content_url

    def _create_settings_dirs(self):
        dirs = [
            f"{self.base_dir}settings",
            f"{self.base_dir}pulp_storage",
            f"{self.base_dir}pgsql",
            f"{self.base_dir}containers"]
        for d in dirs:
            os.makedirs(d)

    def _add_settings(self):
        hostname = socket.gethostname()
        settings_file = '/tmp/pulp/settings/settings.py'
        with open(settings_file, 'w') as f:
            c = f"CONTENT_ORIGIN='{hostname}:8081'\n"
            c = c + f"ANSIBLE_API_HOSTNAME='{self.api_url}'\n"
            c = c + f"ANSIBLE_CONTENT_HOSTNAME='{self.api_url}/pulp/content'\n"
            c = c + "TOKEN_AUTH_DISABLED=True"
            f.writelines(c)

    def _start_pulp(self):
        cwd = '/tmp/pulp/'
        cmd = [
            'podman run --detach \
                --publish 8080:80 \
                --publish 8081:24816 \
                --name galaxy-importer-pulp \
                --volume ./settings:/etc/pulp:Z \
                --volume ./pulp_storage:/var/lib/pulp:Z \
                --volume ./pgsql:/var/lib/pgsql:Z \
                --volume ./containers:/var/lib/containers:Z \
                --device /dev/fuse \
                pulp/pulp-fedora31'
        ]
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            shell=True
        )

        return_code = proc.wait()
        if return_code == 0:
            self._update_admin_account()
        else:
            self.log.error(
                'An exception occurred in {}, returncode={}'
                    .format(' '.join(cmd), return_code))

    def _update_admin_account(self):
        self._server_ready()
        cmd = "podman exec -it galaxy-importer-pulp bash -c 'pulpcore-manager reset-admin-password --password=admin'"
        subprocess.run(cmd, shell=True)

    def _server_ready(self):
        for i in range(API_CHECK_RETRIES):
            try:
                r = requests.get(f'{self.content_url}/v2/')
            except requests.exceptions.ConnectionError:
                continue
            if r.status_code == 200:
                break
            time.sleep(API_CHECK_DELAY_SECONDS)

    def _stop_pulp(self):
        # TODO Refactor shell=True to standard Popen call
        self.log.info('Stopping Pulp server')
        cmd = f'podman stop galaxy-importer-pulp; \
            podman rm galaxy-importer-pulp'
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            shell=True
        )

        return_code = proc.wait()
        if return_code == 0:
            self._remove_pulp_data()
        else:
            self.log.error(
                'An exception occurred in {}, returncode={}'
                    .format(' '.join(cmd), return_code))

    def _remove_pulp_data(self):
        try:
            p = pexpect.spawn("podman unshare", encoding="utf-8")
            p.expect([r'[*#\$] ', pexpect.EOF])
            p.sendline('rm -rf /tmp/pulp\r\n')
            p.expect([r'[*#\$] ', pexpect.EOF])
        except pexpect.exceptions.ExceptionPexpect:
            self.cleanup()

    def cleanup(self):
        self.log.info('Removing Pulp server')
        self._stop_pulp()
