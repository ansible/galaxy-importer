#!/bin/bash

set -e

echo "Starting integration test..."

TMPDIR=$(mktemp -d -t galaxy-importer-XXXXXXXX)
python3 -m venv $TMPDIR/venv
source $TMPDIR/venv/bin/activate
pip install .
cd $TMPDIR

pwd
pip freeze | grep importer


###################################
#   IMPORT SMOKETEST
###################################

python -c 'from galaxy_importer import main'
