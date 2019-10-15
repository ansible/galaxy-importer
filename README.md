### Install

#### From pypi

`pip install galaxy-importer`

#### From source (with pipenv)

Clone repo and go into project directory

Install into environment the local setup.py including its development dependencies:

`pip install -e .[dev]`

### Run importer

Run parsing/validation standalone to view log output and importer result for a build collection artifact file:

`python -m galaxy_importer.main [collection_artifact_file]`

View log output in terminal, and view the importer result in the written file `importer_result.json`
