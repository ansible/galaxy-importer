import json
import logging

from subprocess import Popen
from subprocess import PIPE


default_logger = logging.getLogger(__name__)


class GalaxyCLIWrapper:
    def __init__(self, path=None, fq_collection_name=None, ansible_local_tmp=None, logger=None):

        self.log = logger or default_logger

        # path is the full path to the installed collection
        self.path = path

        # do we really need this? ...
        self.ansible_local_tmp = ansible_local_tmp or "~/.ansible/tmp"

        # collection FQCN but can be enumerated from path
        self.fq_collection_name = fq_collection_name or self._fq_collection_name

    @property
    def _fq_collection_name(self):
        parts = self.path.split("/")
        namespace = parts[-2]
        name = parts[-1]
        return namespace + "." + name

    @property
    def _collections_path(self):
        return "/".join(self.path.split("/")[:-3])

    @property
    def _base_ansible_doc_cmd(self):
        return [
            "/usr/bin/env",
            f"ANSIBLE_COLLECTIONS_PATHS={self._collections_path}",
            f"ANSIBLE_COLLECTIONS_PATH={self._collections_path}",
            f"ANSIBLE_LOCAL_TEMP={self.ansible_local_tmp}",
            "ansible-doc",
        ]

    def doc(self, plugin_type, plugins):
        cmd = (
            self._base_ansible_doc_cmd
            + [
                "--type",
                plugin_type,
                "--json",
            ]
            + plugins
        )
        self.log.debug("CMD: {}".format(" ".join(cmd)))
        proc = Popen(cmd, cwd=self._collections_path, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            self.log.error(
                'Error running ansible-doc: cmd="{cmd}" returncode="{rc}" {err}'.format(
                    cmd=" ".join(cmd), rc=proc.returncode, err=stderr
                )
            )
            return {}
        return json.loads(stdout)

    def list(self, plugin_type, fqcn=None):
        """Use ansible-doc to get a list of plugins for the collection by type."""
        cmd = self._base_ansible_doc_cmd + [
            "--list",
            "--type",
            plugin_type,
            "--json",
            fqcn or self.fq_collection_name,
        ]
        self.log.debug("CMD: {}".format(" ".join(cmd)))
        proc = Popen(cmd, cwd=self._collections_path, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            self.log.error(
                'Error running ansible-doc: cmd="{cmd}" returncode="{rc}" {err}'.format(
                    cmd=" ".join(cmd), rc=proc.returncode, err=stderr
                )
            )
            return {}
        return json.loads(stdout)

    def list_files(self, plugin_type, fqcn=None):
        """Use ansible-doc to get a list of plugins for the collection by type."""
        cmd = self._base_ansible_doc_cmd + [
            "--list_files",
            "--type",
            plugin_type,
            fqcn or self.fq_collection_name,
        ]
        self.log.debug("CMD: {}".format(" ".join(cmd)))
        proc = Popen(cmd, cwd=self._collections_path, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            self.log.error(
                'Error running ansible-doc: cmd="{cmd}" returncode="{rc}" {err}'.format(
                    cmd=" ".join(cmd), rc=proc.returncode, err=stderr
                )
            )
            return {}

        plugins = {}
        for line in stdout.decode("utf-8").split("\n"):
            if not line:
                continue
            words = line.split()
            plugins[(plugin_type, words[0])] = words[1]

        return plugins
