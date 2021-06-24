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
mkdir meta
cd meta
printf "requires_ansible: '>=2.9.10,<2.11.5'" > runtime.yml
cd ..
ansible-galaxy collection build
cd $TMPDIR

# create config file to run ansible-test sanity in locally built container
printf "[galaxy-importer]\nRUN_ANSIBLE_TEST = True\nANSIBLE_TEST_LOCAL_IMAGE = True\nLOCAL_IMAGE_DOCKER = True\n" > galaxy-importer.cfg
export GALAXY_IMPORTER_CONFIG=galaxy-importer.cfg
echo "Using galaxy-importer.cfg:"
cat galaxy-importer.cfg

# run the importer
python3 -m galaxy_importer.main foo/bar/foo-bar-*.tar.gz
RETURN_CODE=$?

# cleanup
cd /tmp
rm -rf $TMPDIR

exit $RETURN_CODE
