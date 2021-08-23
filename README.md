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

#### Structure of Output

* `metadata` (all data from MANIFEST.json, set by CollectionLoader.\_load_collection_manifest())
* `docs_blob` (set by CollectionLoader.\_build_docs_blob())
 * `collection_readme`
 * `documentation_files`
 * `contents`
* `contents`
* `requires_ansible`


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

Configuration options and their defaults are defined in `DEFAULTS` at [galaxy_importer/config.py](galaxy_importer/config.py)

Example configuration file with subset of config options:

```
[galaxy-importer]
LOG_LEVEL_MAIN = INFO
RUN_ANSIBLE_TEST = False
ANSIBLE_LOCAL_TMP = '~/.ansible/tmp'
```

- `RUN_ANSIBLE_TEST` - Set to `True` to run `ansible-test` during collection import. Defaults to `False`.

- `ANSIBLE_TEST_LOCAL_IMAGE` - Set to `True` to run `ansible-test` sandboxed within a container image. Requires installation of either Podman or Docker to run the container. Defaults to `False`.

- `LOCAL_IMAGE_DOCKER` - Set to `True` to run the `ansible-test` container image via Docker; otherwise, Podman will be used. Defaults to `False`.

### Issues and Process

To file an issue, visit the [Automation Hub Jira project](https://issues.redhat.com/projects/AAH/issues)

Process details for `galaxy-importer`: [PROCESS.md](PROCESS.md)
