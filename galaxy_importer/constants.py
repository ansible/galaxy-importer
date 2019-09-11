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

import enum
import re


MAX_TAGS_COUNT = 20
NAME_REGEXP = re.compile(r'^(?!.*__)[a-z]+[0-9a-z_]*$')
CONTENT_NAME_REGEXP = re.compile(r'^(?!.*__)[a-z_]+[0-9a-z_]*$')


class ContentCategory(enum.Enum):
    MODULE = 'module'
    ROLE = 'role'
    PLUGIN = 'plugin'
    PLAYBOOK = 'playbook'


class ContentType(enum.Enum):
    ROLE = 'role'
    MODULE = 'module'
    MODULE_UTILS = 'module_utils'
    ACTION_PLUGIN = 'action'
    BECOME_PLUGIN = 'become'
    CACHE_PLUGIN = 'cache'
    CALLBACK_PLUGIN = 'callback'
    CLICONF_PLUGIN = 'cliconf'
    CONNECTION_PLUGIN = 'connection'
    DOC_FRAGMENTS_PLUGIN = 'doc_fragments'
    FILTER_PLUGIN = 'filter'
    HTTPAPI_PLUGIN = 'httpapi'
    INVENTORY_PLUGIN = 'inventory'
    LOOKUP_PLUGIN = 'lookup'
    NETCONF_PLUGIN = 'netconf'
    SHELL_PLUGIN = 'shell'
    STRATEGY_PLUGIN = 'strategy'
    TERMINAL_PLUGIN = 'terminal'
    TEST_PLUGIN = 'test'
    VARS_PLUGIN = 'vars'

    @property
    def category(self):
        return {
            ContentType.ROLE: ContentCategory.ROLE,
            ContentType.MODULE: ContentCategory.MODULE,
            ContentType.MODULE_UTILS: ContentCategory.PLUGIN,
            ContentType.ACTION_PLUGIN: ContentCategory.PLUGIN,
            ContentType.BECOME_PLUGIN: ContentCategory.PLUGIN,
            ContentType.CACHE_PLUGIN: ContentCategory.PLUGIN,
            ContentType.CALLBACK_PLUGIN: ContentCategory.PLUGIN,
            ContentType.CLICONF_PLUGIN: ContentCategory.PLUGIN,
            ContentType.CONNECTION_PLUGIN: ContentCategory.PLUGIN,
            ContentType.DOC_FRAGMENTS_PLUGIN: ContentCategory.PLUGIN,
            ContentType.FILTER_PLUGIN: ContentCategory.PLUGIN,
            ContentType.HTTPAPI_PLUGIN: ContentCategory.PLUGIN,
            ContentType.INVENTORY_PLUGIN: ContentCategory.PLUGIN,
            ContentType.LOOKUP_PLUGIN: ContentCategory.PLUGIN,
            ContentType.NETCONF_PLUGIN: ContentCategory.PLUGIN,
            ContentType.SHELL_PLUGIN: ContentCategory.PLUGIN,
            ContentType.STRATEGY_PLUGIN: ContentCategory.PLUGIN,
            ContentType.TERMINAL_PLUGIN: ContentCategory.PLUGIN,
            ContentType.TEST_PLUGIN: ContentCategory.PLUGIN,
            ContentType.VARS_PLUGIN: ContentCategory.PLUGIN,
        }.get(self)
