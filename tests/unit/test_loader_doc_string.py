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
import os
import tempfile
from unittest import mock

import pytest
import shutil

from galaxy_importer import config
from galaxy_importer import loaders


FIL_PY = """
def fil_one(): pass

def fil_two(): pass

class FilterModule(object):
    def filters(self):
        return {
            'fil_one': fil_one,
            'fil_two': fil_two,
        }
"""

FIL_ONE_YML = """
DOCUMENTATION:
  name: fil_one
  short_description: Do nothing filter one
  author: Connor
"""

FIL_TWO_YML = """
DOCUMENTATION:
  name: fil_two
  short_description: Do nothing filter two
  author: Zach
"""


@pytest.fixture
def plugins_collection_root():
    try:
        tmp_dir = tempfile.TemporaryDirectory().name
        sub_path = "ansible_collections/my_namespace/my_collection"
        collection_root = os.path.join(tmp_dir, sub_path)
        os.makedirs(collection_root)
        os.mkdir(os.path.join(collection_root, "plugins"))
        yield collection_root
    finally:
        shutil.rmtree(tmp_dir)


@pytest.fixture
def doc_string_loader():
    cfg = config.Config(config_data=config.ConfigFile.load())
    return loaders.DocStringLoader(
        path="/tmp_dir/tmp123/ansible_collections/my_namespace/my_collection",
        fq_collection_name="my_namespace.my_collection",
        cfg=cfg,
    )


def test_init_loader(doc_string_loader):
    assert doc_string_loader.fq_collection_name == "my_namespace.my_collection"


def test_get_plugins(plugins_collection_root):
    loader = loaders.DocStringLoader(
        path=plugins_collection_root,
        fq_collection_name="my_namespace.my_collection",
        cfg=config.Config(config_data=config.ConfigFile.load()),
    )

    # Test single cache plugin.
    cache_dir = os.path.join(plugins_collection_root, "plugins", "cache")
    os.mkdir(cache_dir)
    with open(os.path.join(cache_dir, "this.py"), "w+") as fh:
        fh.write("")
    plugins = loader._get_plugins_of_type("cache")
    assert plugins == ["my_namespace.my_collection.this"]

    # Test multiple connection plugins.
    connection_dir = os.path.join(plugins_collection_root, "plugins", "connection")
    os.mkdir(connection_dir)
    with open(os.path.join(connection_dir, "qwe.py"), "w+") as fh:
        fh.write("")
    with open(os.path.join(plugins_collection_root, "plugins", "connection", "rty.py"), "w+") as fh:
        fh.write("")
    plugins = loader._get_plugins_of_type("connection")
    assert plugins == ["my_namespace.my_collection.qwe", "my_namespace.my_collection.rty"]

    # Test multiple inventory plugins including a nested directory.
    inventory_dir = os.path.join(plugins_collection_root, "plugins", "inventory")
    nested_dir = os.path.join(inventory_dir, "nested")
    os.makedirs(nested_dir)
    with open(os.path.join(inventory_dir, "ans.py"), "w+") as fh:
        fh.write("")
    with open(os.path.join(nested_dir, "ible.py"), "w+") as fh:
        fh.write("")
    plugins = loader._get_plugins_of_type("inventory")
    assert plugins == ["my_namespace.my_collection.ans", "my_namespace.my_collection.nested.ible"]


@mock.patch("galaxy_importer.loaders.doc_string.Popen")
def test_run_ansible_doc(mocked_popen, doc_string_loader):
    mocked_popen.return_value.communicate.return_value = ('"expected output"', "")
    mocked_popen.return_value.returncode = 0
    res = doc_string_loader._run_ansible_doc(plugin_type="", plugins=[])
    assert res == "expected output"


@mock.patch("galaxy_importer.loaders.doc_string.Popen")
def test_run_ansible_doc_exception(mocked_popen, doc_string_loader):
    mocked_popen.return_value.communicate.return_value = (
        "output",
        "error that causes exception",
    )
    mocked_popen.return_value.returncode = 1
    res = doc_string_loader._run_ansible_doc(plugin_type="", plugins=[])
    assert not res


@mock.patch.object(loaders.DocStringLoader, "_get_plugins_of_type")
def test_ansible_doc_no_plugins(mocked_get_plugins_of_type, doc_string_loader):
    mocked_get_plugins_of_type.return_value = []
    assert doc_string_loader.load() == {}


def test_process_doc_strings_not_dict(doc_string_loader):
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
    res = doc_string_loader._process_doc_strings(data)
    assert res["my_sample_module"]["return"] == [
        {
            "name": "message",
            "description": ["The output message the sample module generates"],
        },
        {
            "name": "original_message",
            "description": ["The original name param that was passed in"],
            "type": "str",
        },
    ]


def test_transform_doc_strings_return(doc_string_loader):
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
    assert transformed_data["return"] == [
        {
            "name": "message",
            "description": ["The output message the sample module generates"],
        },
        {
            "name": "original_message",
            "description": ["The original name param that was passed in"],
            "type": "str",
        },
    ]


def test_transform_doc_strings_options(doc_string_loader):
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
    assert transformed_data["doc"]["options"] == [
        {
            "name": "exclude",
            "description": ["This is the message to send..."],
            "required": "true",
        },
        {
            "name": "use_new",
            "description": ["Control is passed..."],
            "version_added": "2.7",
            "default": "auto",
        },
    ]


def test_transform_doc_strings_nested_contains(doc_string_loader):
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
    assert transformed_data["return"] == [
        {
            "name": "resources",
            "contains": [
                {
                    "name": "acceleratorType",
                    "description": ["The type of..."],
                    "returned": "success",
                },
                {
                    "name": "networkEndpoints",
                    "contains": [
                        {
                            "name": "ipAddress",
                            "description": ["The IP address."],
                            "type": "str",
                        },
                        {
                            "name": "port",
                            "description": ["The port"],
                            "type": "int",
                        },
                    ],
                },
            ],
        },
    ]


def test_transform_doc_strings_nested_contains_dict_of_list(doc_string_loader):
    ansible_doc_output = """
        {
            "my_sample_module": {
                "return": {
                    "output": {
                        "contains": {
                            "formatted_output": [
                                "Contains formatted response ..."
                            ]
                        }
                    }
                }
            }
        }
    """
    data = json.loads(ansible_doc_output)
    data = list(data.values())[0]
    transformed_data = doc_string_loader._transform_doc_strings(data)
    assert transformed_data["return"] == [
        {"name": "output", "contains": []},
    ]


def test_transform_doc_strings_nested_suboptions(doc_string_loader):
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
    assert transformed_data["doc"]["options"] == [
        {
            "name": "exclude",
            "description": ["This is the message to send..."],
            "required": "true",
        },
        {
            "name": "lan2_port_setting",
            "description": ["Control is passed..."],
            "suboptions": [
                {
                    "name": "enabled",
                    "description": ["If set to True..."],
                    "type": "bool",
                },
                {
                    "name": "network_setting",
                    "description": ["If the enable field..."],
                    "suboptions": [
                        {
                            "name": "address",
                            "description": ["The IPv4 Address of LAN2"],
                        },
                        {
                            "name": "gateway",
                            "description": ["The default gateway of LAN2"],
                        },
                    ],
                },
            ],
        },
    ]


@mock.patch.object(loaders.DocStringLoader, "_get_plugins_of_type")
@mock.patch.object(loaders.DocStringLoader, "_run_ansible_doc")
def test_load(mocked_run_ansible_doc, mocked_get_plugins_of_type, doc_string_loader):
    ansible_doc_output = """
        {
            "my_module": {
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
    mocked_run_ansible_doc.return_value = json.loads(ansible_doc_output)

    def mocked_get_plugins_func(plugin_type):
        return ["my_namespace.my_collection.my_module"] if plugin_type == "module" else []

    mocked_get_plugins_of_type.side_effect = mocked_get_plugins_func

    res = doc_string_loader.load()
    assert res == {
        "module": {
            "my_module": {
                "return": [
                    {
                        "description": ["The output message the sample module generates"],
                        "name": "message",
                    },
                    {
                        "description": ["The original name param that was passed in"],
                        "name": "original_message",
                        "type": "str",
                    },
                ]
            }
        }
    }


def test_filter_plugin_yml_doc(plugins_collection_root):
    loader = loaders.DocStringLoader(
        path=plugins_collection_root,
        fq_collection_name="my_namespace.my_collection",
        cfg=config.Config(config_data=config.ConfigFile.load()),
    )

    filter_dir = os.path.join(plugins_collection_root, "plugins", "filter")
    os.mkdir(filter_dir)
    with open(os.path.join(filter_dir, "fil.py"), "w+") as fh:
        fh.write(FIL_PY)
    with open(os.path.join(filter_dir, "fil_one.yml"), "w+") as fh:
        fh.write(FIL_ONE_YML)
    with open(os.path.join(filter_dir, "fil_two.yml"), "w+") as fh:
        fh.write(FIL_TWO_YML)
    result = loader.load()
    assert result == {
        "filter": {
            "my_namespace.my_collection.fil_one": {
                "doc": {
                    "author": "Connor",
                    "collection": "my_namespace.my_collection",
                    "filename": os.path.join(
                        plugins_collection_root, "plugins", "filter", "fil_one.yml"
                    ),
                    "name": "fil_one",
                    "short_description": "Do nothing filter one",
                },
                "examples": None,
                "metadata": None,
                "return": None,
            },
            "my_namespace.my_collection.fil_two": {
                "doc": {
                    "author": "Zach",
                    "collection": "my_namespace.my_collection",
                    "filename": os.path.join(
                        plugins_collection_root, "plugins", "filter", "fil_two.yml"
                    ),
                    "name": "fil_two",
                    "short_description": "Do nothing filter two",
                },
                "examples": None,
                "metadata": None,
                "return": None,
            },
        }
    }


@mock.patch.object(loaders.DocStringLoader, "_get_plugins_of_type")
@mock.patch("galaxy_importer.loaders.doc_string.Popen")
def test_load_ansible_doc_error(mocked_popen, mocked_get_plugins_of_type, doc_string_loader):
    mocked_popen.return_value.communicate.return_value = (
        "output",
        "error that causes exception",
    )
    mocked_popen.return_value.returncode = 1

    def mocked_get_plugins_func(plugin_type):
        return ["my_namespace.my_collection.my_plugin"] if plugin_type == "inventory" else []

    mocked_get_plugins_of_type.side_effect = mocked_get_plugins_func

    res = doc_string_loader.load()
    assert res == {"inventory": {}}


@mock.patch("shutil.which")
def test_no_ansible_doc_bin(mocked_shutil_which, doc_string_loader, tmpdir, caplog):
    mocked_shutil_which.return_value = False

    doc_string_loader.path = str(tmpdir)
    tmpdir.mkdir("plugins").mkdir("inventory").join("my_plugin.py").write("")

    doc_string_loader.load()
    assert "ansible-doc not found, skipping loading of docstrings" in [
        r.message for r in caplog.records
    ]
