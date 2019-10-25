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
from unittest import mock

from galaxy_importer import constants
from galaxy_importer import loaders


ANSIBLE_DOC_OUTPUT = """
    {"my_sample_module": {
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
        },
        "examples": null,
        "metadata": null,
        "return": {
            "message": {
                "description": "The output message the sample module generates"
            },
            "original_message": {
                "description": "The original name param that was passed in",
                "type": "str"
            }
        }
    }}
"""


@pytest.fixture
def doc_string_loader():
    return loaders.DocStringLoader(
        content_type=constants.ContentType.MODULE.value,
        path=None,
        fq_name='my_namespace.my_collection.my_sample_module')


def test_init_loader(doc_string_loader):
    assert doc_string_loader.content_type == 'module'
    assert doc_string_loader.fq_name == 'my_namespace.my_collection.my_sample_module'


@mock.patch('galaxy_importer.loaders.Popen')
def test_run_ansible_doc(mocked_popen, doc_string_loader):
    mocked_popen.return_value.communicate.return_value = (
        'expected output', '')
    mocked_popen.return_value.returncode = 0
    res = doc_string_loader._run_ansible_doc()
    assert res == 'expected output'


@mock.patch('galaxy_importer.loaders.Popen')
def test_run_ansible_doc_exception(mocked_popen, doc_string_loader):
    mocked_popen.return_value.communicate.return_value = (
        'output', 'error that causes exception')
    mocked_popen.return_value.returncode = 1
    res = doc_string_loader._run_ansible_doc()
    assert not res


def test_ansible_doc_unsupported_type():
    action_plugin_loader = loaders.DocStringLoader(
        content_type=constants.ContentType.ACTION_PLUGIN.value,
        path=None,
        fq_name='my_namespace.my_collection.my_sample_module')
    assert constants.ContentType.ACTION_PLUGIN.value not in loaders.ANSIBLE_DOC_SUPPORTED_TYPES
    assert not action_plugin_loader.load()


@mock.patch.object(loaders.DocStringLoader, '_run_ansible_doc')
def test_ansible_doc_no_output(mocked_run_ansible_doc, doc_string_loader):
    mocked_run_ansible_doc.return_value = ''
    assert doc_string_loader.load() is None


@mock.patch.object(loaders.DocStringLoader, '_run_ansible_doc')
def test_get_doc_strings(mocked_run_ansible_doc, doc_string_loader):
    mocked_run_ansible_doc.return_value = ANSIBLE_DOC_OUTPUT
    doc_strings = doc_string_loader.load()
    assert doc_strings['doc']['version_added'] == '2.8'
    assert doc_strings['doc']['description'] == \
        ['Sample module for testing.']

    mocked_run_ansible_doc.return_value = '{}'
    doc_strings = doc_string_loader.load()
    assert not doc_strings

    mocked_run_ansible_doc.return_value = '[]'
    doc_strings = doc_string_loader.load()
    assert not doc_strings


def test_return(doc_string_loader):
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
    data = list(data.values())[0]
    transformed_data = doc_string_loader._transform_doc_strings(data)
    assert transformed_data['return'] == [
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


def test_doc_options(doc_string_loader):
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
    data = list(data.values())[0]
    transformed_data = doc_string_loader._transform_doc_strings(data)
    assert transformed_data['doc']['options'] == [
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


def test_return_nested_contains(doc_string_loader):
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
    data = list(data.values())[0]
    transformed_data = doc_string_loader._transform_doc_strings(data)
    assert transformed_data['return'] == [
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


def test_doc_nested_suboptions(doc_string_loader):
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
    data = list(data.values())[0]
    transformed_data = doc_string_loader._transform_doc_strings(data)
    assert transformed_data['doc']['options'] == [
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
