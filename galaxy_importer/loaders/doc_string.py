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

from copy import deepcopy
import json
import logging
import shutil
from subprocess import Popen, PIPE

from galaxy_importer import constants

default_logger = logging.getLogger(__name__)


class DocStringLoader:
    """Process ansible-doc doc strings for entire collection.

    Load by calling ansible-doc once in batch for each plugin type."""

    def __init__(self, path, fq_collection_name, cfg, logger=None):
        self.path = path
        self.fq_collection_name = fq_collection_name
        self.cfg = cfg
        self.log = logger or default_logger

    def load(self):
        self.log.info("Getting doc strings via ansible-doc")
        docs = {}

        if not shutil.which("ansible-doc"):
            self.log.warning("ansible-doc not found, skipping loading of docstrings")
            return docs

        for plugin_type in constants.ANSIBLE_DOC_SUPPORTED_TYPES:
            plugins = self._get_plugins_of_type(plugin_type)

            if not plugins:
                continue

            data = self._run_ansible_doc(plugin_type, plugins)
            data = self._process_doc_strings(data)
            docs[plugin_type] = data

        return docs

    def _get_plugins_of_type(self, plugin_type: str) -> list[str]:
        """Get list of fully qualified plugins names of a type.

        This function uses ansible-doc to parse the names of all plugins
        for this collection (self.fq_collection_name) of the given plugin
        type. An alternate strategy may be to walk the collection directory
        and find plugins. However, that gets murky with filter and test plugins
        which may have either inline-python documentation or adjacent-yaml
        documentation. This way, ansible-doc does the hard work for us.
        """
        collections_path = "/".join(self.path.split("/")[:-3])

        # This command invokes ansible-doc to list the names of all plugins
        # of the given plugin type. The output is a json dictionary in which
        # the keys are the plugin names and the values are short descriptions.
        # We only care about the names.
        cmd = [
            "/usr/bin/env",
            f"ANSIBLE_COLLECTIONS_PATHS={collections_path}",
            f"ANSIBLE_LOCAL_TEMP={self.cfg.ansible_local_tmp}",
            "ansible-doc",
            "--type",
            plugin_type,
            "--list",
            "--json",
            self.fq_collection_name
        ]
        proc = Popen(cmd, cwd=collections_path, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()

        # If ansible-doc fails for any reason, log the error and return
        # the empty list.
        if proc.returncode:
            self.log.error(
                'Error running ansible-doc: cmd="{cmd}" returncode="{rc}" {err}'.format(
                    cmd=" ".join(cmd), rc=proc.returncode, err=stderr
                )
            )
            return list()

        # Success! Load the ansible-doc output into a python
        # dictionary and returns a list of the keys.
        result = json.loads(stdout)
        return list(result.keys())

    def _run_ansible_doc(self, plugin_type, plugins):
        collections_path = "/".join(self.path.split("/")[:-3])
        cmd = [
            "/usr/bin/env",
            f"ANSIBLE_COLLECTIONS_PATHS={collections_path}",
            f"ANSIBLE_LOCAL_TEMP={self.cfg.ansible_local_tmp}",
            "ansible-doc",
            "--type",
            plugin_type,
            "--json",
        ] + plugins
        self.log.debug("CMD: {}".format(" ".join(cmd)))
        proc = Popen(cmd, cwd=collections_path, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode:
            self.log.error(
                'Error running ansible-doc: cmd="{cmd}" returncode="{rc}" {err}'.format(
                    cmd=" ".join(cmd), rc=proc.returncode, err=stderr
                )
            )
            return {}
        return json.loads(stdout)

    def _process_doc_strings(self, doc_strings):
        processed_doc_strings = {}
        for plugin_key, value in doc_strings.items():
            processed_doc_strings[plugin_key] = self._transform_doc_strings(value, self.log)
        return processed_doc_strings

    @staticmethod
    def _transform_doc_strings(data, logger=default_logger):
        """Transform data meant for UI tables into format suitable for UI."""

        def dict_to_named_list(dict_of_dict):
            """Return new list of dicts for given dict of dicts."""
            try:
                return [{"name": key, **deepcopy(dict_of_dict[key])} for key in dict_of_dict.keys()]
            except TypeError:
                logger.warning(f"Expected this to be a dictionary of dictionaries: {dict_of_dict}")
                return [
                    {"name": key, **deepcopy(dict_of_dict[key])}
                    for key in dict_of_dict.keys()
                    if isinstance(key, dict)
                ]

        def handle_nested_tables(obj, table_key):
            """Recurse over dict to replace nested tables with updated format."""
            if table_key in obj.keys() and isinstance(obj[table_key], dict):
                obj[table_key] = dict_to_named_list(obj[table_key])
                for row in obj[table_key]:
                    handle_nested_tables(row, table_key)

        doc = data.get("doc", {})
        if isinstance(doc.get("options"), dict):
            doc["options"] = dict_to_named_list(doc["options"])
            for d in doc["options"]:
                handle_nested_tables(d, table_key="suboptions")

        ret = data.get("return", None)
        if ret and isinstance(ret, dict):
            data["return"] = dict_to_named_list(ret)
            for d in data["return"]:
                handle_nested_tables(d, table_key="contains")

        return data
