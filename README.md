### Ansible Requirements

``galaxy-importer`` requires the following other Ansible projects:

* ``ansible-lint`` up to [24.9.0](https://github.com/ansible/ansible-lint/tree/v24.9.0/docs)
* ``ansible-core`` up to [2.16](https://docs.ansible.com/ansible-core/2.16/index.html)

If you are installing from source, see ``setup.cfg`` in the repository for the matching requirements.

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

Supports legacy roles (note: must be in the parent directory of the legacy role):

`python -m galaxy_importer.main --legacy-role [legacy_role_directory] --namespace [namespace]`

Supports converting markdown to html:

`python -m galaxy_importer.main --markdown [readme_md_directory]`

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

- `ANSIBLE_LOCAL_TMP` - Set to any desired local Ansible temp directory. Defaults to `~/.ansible/tmp`.

- `ANSIBLE_TEST_LOCAL_IMAGE` - Set to `True` to run `ansible-test` sandboxed within a container image. Requires installation of either Podman or Docker to run the container. Defaults to `False`.

- `CHECK_CHANGELOG` - Set to `False` to not check for a `CHANGELOG.rst or` `CHANGELOG.md` file under the collection root or `docs/` dir, or a `changelogs/changelog.(yml/yaml)` file. Defaults to `True`. 

- `CHECK_REQUIRED_TAGS` - Set to `True` to check for a set of tags required for Ansible collection certification. Defaults to `False`. 

- `LOCAL_IMAGE_DOCKER` - Set to `True` to run the `ansible-test` container image via Docker; otherwise, Podman will be used. Defaults to `False`.

- `LOG_LEVEL_MAIN` - Set to the desired log level. Defaults to `INFO`. 

- `OFFLINE_ANSIBLE_LINT` - Set to `False` if you want `ansible-lint` to check for a new version. Defaults to `True`.

- `REQUIRE_V1_OR_LATER` - Set to `True` to require a version number `1.0.0` or greater. Defaults to `False`.

- `RUN_ANSIBLE_DOC` - Set to `False` to skip `ansible-doc`. Defaults to `True`.

- `RUN_ANSIBLE_LINT` - Set to `False` to skip running `ansible-lint --profile production` over the whole collection. Defaults to `True`. 

- `RUN_ANSIBLE_TEST` - Set to `True` to run `ansible-test` during collection import. Defaults to `False`.

- `RUN_FLAKE8` - Set to `True` to run flake8. Defaults to `False`. 


### Issues and Process

To file an issue, visit the [Automation Hub Jira project](https://issues.redhat.com/projects/AAH/issues)

Process details for `galaxy-importer`: [PROCESS.md](PROCESS.md)


### Additional Notes

Place `.md` files in the `docs/` dir to have them show up in an imported collection's "Documentation" tab on Galaxy or Automation Hub.  
