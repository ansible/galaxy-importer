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
from unittest import mock

import pytest

from galaxy_importer import config
from galaxy_importer import loaders


ANSIBLE_DOC_OUTPUT = json.loads(
    """
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
)


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


def test_get_plugins(doc_string_loader, tmpdir):
    tmpdir.join("__init__.py").write("")
    tmpdir.join("should_be_ignored.txt").write("")
    tmpdir.join("my_module.py").write("")
    plugins = doc_string_loader._get_plugins(str(tmpdir))
    assert plugins == ["my_namespace.my_collection.my_module"]


def test_get_plugins_subdirs(doc_string_loader, tmpdir):
    tmpdir.mkdir("subdir1").mkdir("subdir2").join("nested_plugin.py").write("")
    plugins = doc_string_loader._get_plugins(str(tmpdir))
    assert plugins == ["my_namespace.my_collection.subdir1.subdir2.nested_plugin"]


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


@mock.patch("galaxy_importer.loaders.doc_string.constants.ANSIBLE_DOC_SUPPORTED_TYPES", ["module"])
@mock.patch.object(loaders.DocStringLoader, "_run_ansible_doc_list", return_value={})
@mock.patch.object(loaders.DocStringLoader, "_run_ansible_doc", return_value={})
def test_ansible_doc_no_output(
    mocked_run_ansible_doc_list, mocked_run_ansible_doc, doc_string_loader
):
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


@mock.patch("galaxy_importer.loaders.doc_string.constants.ANSIBLE_DOC_SUPPORTED_TYPES", ["module"])
@mock.patch.object(loaders.DocStringLoader, "_run_ansible_doc_list", return_value={"my_module": {}})
@mock.patch.object(loaders.DocStringLoader, "_run_ansible_doc", return_value=ANSIBLE_DOC_OUTPUT)
def test_load_function(
    mocked_run_ansible_doc_list, mocked_run_ansible_doc, doc_string_loader, tmpdir
):
    doc_string_loader.path = str(tmpdir)
    tmpdir.mkdir("plugins").mkdir("modules").join("my_module.py").write("")

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


@mock.patch(
    "galaxy_importer.loaders.doc_string.constants.ANSIBLE_DOC_SUPPORTED_TYPES", ["inventory"]
)
@mock.patch.object(loaders.DocStringLoader, "_run_ansible_doc_list", return_value={"my_plugin": {}})
@mock.patch("galaxy_importer.loaders.doc_string.Popen")
def test_load_ansible_doc_error(mocked_popen, mocked_doc_list, doc_string_loader, tmpdir):
    mocked_popen.return_value.communicate.return_value = (
        "output",
        "error that causes exception",
    )
    mocked_popen.return_value.returncode = 1

    doc_string_loader.path = str(tmpdir)
    tmpdir.mkdir("plugins").mkdir("inventory").join("my_plugin.py").write("")

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
