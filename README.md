### Install

#### From pypi

`pip install galaxy-importer`

#### From source

Clone repo and go into project directory

Install into environment the local setup.py including its development dependencies:

`pip install -e .[dev]`

### Run importer

Run parsing/validation standalone to view log output and importer result for a build collection artifact file:

`python -m galaxy_importer.main [collection_artifact_file]`

View log output in terminal, and view the importer result in the written file `importer_result.json`


### Configuration

An optional ini configuration file is supported, the following locations are checked in this order:

```
/etc/galaxy-importer/galaxy-importer.cfg
<code_source>/galaxy_importer/galaxy-importer.cfg
```

You can override the above paths by setting `GALAXY_IMPORTER_CONFIG` in the environment. For example:

```
$ export GALAXY_IMPORTER_CONFIG=~/galaxy-importer.cfg
```

Example configuration file:

```
[galaxy-importer]
LOG_LEVEL_MAIN = INFO
RUN_FLAKE8 = False
RUN_ANSIBLE_TEST = False
INFRA_PULP = False
INFRA_OSD = False
```

### Issues and Process

Issues can be reported in the [galaxy_ng](https://github.com/ansible/galaxy_ng) repository

Process details for `galaxy-importer`: [PROCESS.md](https://github.com/ansible/galaxy-importer/blob/master/PROCESS.md)
