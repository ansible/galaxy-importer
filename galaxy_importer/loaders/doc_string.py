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
import logging
import shutil

from galaxy_importer import constants
from galaxy_importer.galaxy_cli import GalaxyCLIWrapper


default_logger = logging.getLogger(__name__)


class DocStringLoader:
    """Process ansible-doc doc strings for entire collection.

    Load by calling ansible-doc once in batch for each plugin type."""

    def __init__(self, path, fq_collection_name, cfg, logger=None):
        self.path = path
        self.fq_collection_name = fq_collection_name
        self.cfg = cfg
        self.log = logger or default_logger
        self.galaxy_cli = GalaxyCLIWrapper(path=path, fq_collection_name=fq_collection_name)

    def load(self):
        self.log.info("Getting doc strings via ansible-doc")
        docs = {}

        if not shutil.which("ansible-doc"):
            self.log.warning("ansible-doc not found, skipping loading of docstrings")
            return docs

        for plugin_type in constants.ANSIBLE_DOC_SUPPORTED_TYPES:
            # use ansible-doc to list all the plugins of this type
            found_plugins = self.galaxy_cli.list(plugin_type)
            plugins = sorted(list(found_plugins.keys()))

            if not plugins:
                continue

            # get the plugin docs with galaxy
            data = self.galaxy_cli.doc(plugin_type, plugins)
            # make ui suitable data
            data = self._process_doc_strings(data)
            docs[plugin_type] = data

        return docs

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
