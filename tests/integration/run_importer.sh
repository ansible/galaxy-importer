#!/bin/bash

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

###################################
#   RUNTIME VALIDATION
###################################

# make and build a collection
ansible-galaxy collection init foo.bar
cd foo/bar
ansible-galaxy collection build

# run the importer
cd $TMPDIR
python3 -m galaxy_importer.main foo/bar/foo-bar-*.tar.gz
RETURN_CODE=$?

# cleanup
cd /tmp
rm -rf $TMPDIR

exit $RETURN_CODE
