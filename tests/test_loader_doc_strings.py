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

import json
import pytest

from galaxy_importer import constants
from galaxy_importer import loaders


@pytest.fixture
def loader_module():
    return loaders.PluginLoader(
        content_type=constants.ContentType.MODULE,
        rel_path='plugins/modules/my_sample_module.py',
        root='/tmp/tmpiskt5e2n')


def test_doc_options(loader_module):
    ansible_doc_output = """
        {
            "my_sample_module": {
                "doc": {
                    "description": ["Sample module for testing."],
                    "short_description": "Sample module for testing",
                    "version_added": "2.8",
                    "options": {
                        "exclude": {
                            "description": ["This is the message to send..."],
                            "required": "true"
                        },
                        "use_new": {
                            "description": ["Control is passed..."],
                            "version_added": "2.7",
                            "default": "auto"
                        }
                    }
                }
            }
        }
    """
    data = json.loads(ansible_doc_output)
    transformed_data = loader_module._transform_doc_strings(data)
    assert transformed_data['my_sample_module']['doc']['options'] == [
        {
            'name': 'exclude',
            'description': ['This is the message to send...'],
            'required': 'true',
        },
        {
            'name': 'use_new',
            'description': ['Control is passed...'],
            'version_added': '2.7',
            'default': 'auto'
        }
    ]


def test_doc_nested_suboptions(loader_module):
    ansible_doc_output = """
        {
            "my_sample_module": {
                "doc": {
                    "description": ["Sample module for testing."],
                    "short_description": "Sample module for testing",
                    "version_added": "2.8",
                    "options": {
                        "exclude": {
                            "description": ["This is the message to send..."],
                            "required": "true"
                        },
                        "lan2_port_setting": {
                            "description": ["Control is passed..."],
                            "suboptions": {
                                "enabled": {
                                    "description": ["If set to True..."],
                                    "type": "bool"
                                },
                                "network_setting": {
                                    "description": ["If the enable field..."],
                                    "suboptions": {
                                        "address": {
                                            "description": ["The IPv4 Address of LAN2"]
                                        },
                                        "gateway": {
                                            "description": ["The default gateway of LAN2"]
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    data = json.loads(ansible_doc_output)
    transformed_data = loader_module._transform_doc_strings(data)
    assert transformed_data['my_sample_module']['doc']['options'] == [
        {
            'name': 'exclude',
            'description': ['This is the message to send...'],
            'required': 'true',
        },
        {
            'name': 'lan2_port_setting',
            'description': ['Control is passed...'],
            'suboptions': [
                {
                    'name': 'enabled',
                    'description': ['If set to True...'],
                    'type': 'bool',
                },
                {
                    'name': 'network_setting',
                    'description': ['If the enable field...'],
                    'suboptions': [
                        {
                            'name': 'address',
                            'description': ['The IPv4 Address of LAN2'],
                        },
                        {
                            'name': 'gateway',
                            'description': ['The default gateway of LAN2'],
                        }
                    ]
                }
            ]
        }
    ]


def test_return(loader_module):
    ansible_doc_output = """
        {
            "my_sample_module": {
                "return": {
                    "message": {
                        "description": ["The output message the sample module generates"]
                    },
                    "original_message": {
                        "description": ["The original name param that was passed in"],
                        "type": "str"
                    }
                }
            }
        }
    """

    data = json.loads(ansible_doc_output)
    transformed_data = loader_module._transform_doc_strings(data)
    assert transformed_data['my_sample_module']['return'] == [
        {
            'name': 'message',
            'description': ['The output message the sample module generates']
        },
        {
            'name': 'original_message',
            'description': ['The original name param that was passed in'],
            'type': 'str'
        }
    ]


def test_return_nested_contains(loader_module):
    ansible_doc_output = """
        {
            "my_sample_module": {
                "return": {
                    "resources": {
                        "contains": {
                            "acceleratorType": {
                                "description": ["The type of..."],
                                "returned": "success"
                            },
                            "networkEndpoints": {
                                "contains": {
                                    "ipAddress": {
                                        "description": ["The IP address."],
                                        "type": "str"
                                    },
                                    "port": {
                                        "description": ["The port"],
                                        "type": "int"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    """

    data = json.loads(ansible_doc_output)
    transformed_data = loader_module._transform_doc_strings(data)
    assert transformed_data['my_sample_module']['return'] == [
        {
            'name': 'resources',
            'contains': [
                {
                    'name': 'acceleratorType',
                    'description': ['The type of...'],
                    'returned': 'success',
                },
                {
                    'name': 'networkEndpoints',
                    'contains': [
                        {
                            'name': 'ipAddress',
                            'description': ['The IP address.'],
                            'type': 'str',
                        },
                        {
                            'name': 'port',
                            'description': ['The port'],
                            'type': 'int',
                        },
                    ]
                }
            ]
        },
    ]
