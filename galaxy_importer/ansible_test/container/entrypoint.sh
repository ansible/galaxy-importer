#!/bin/bash


function download_archive {
  echo "Downloading collection archive..."
  wget $ARCHIVE_URL -q -O /archive/archive.tar.gz
}

set -e

# Extract collection to path needed for ansible-test sanity
mkdir -p /ansible_collections/placeholder_namespace/placeholder_name
pushd ansible_collections/ > /dev/null
pushd placeholder_namespace/placeholder_name/ > /dev/null

case $1 in
  # run via local image, do not download archive
  LOCAL_IMAGE_RUNNER)
    ;;

  # default, run via openshift, download archive
  *)
    download_archive
    ;;
esac

echo "Extracting archive..."
cp /archive/archive.tar.gz .
tar -xzf archive.tar.gz

# Get variables from collection metadata
read NAMESPACE NAME VERSION < <(python3 <<EOF
import json
with open('MANIFEST.json') as fp:
    metadata = json.load(fp)['collection_info']
values = metadata['namespace'], metadata['name'], metadata['version']
print(*values)
EOF
)

# Rename placeholders in path
popd > /dev/null
mv placeholder_namespace/placeholder_name placeholder_namespace/"$NAME"
mv placeholder_namespace/ "$NAMESPACE"

COLLECTION_DIR=/ansible_collections/"$NAMESPACE"/"$NAME"

cd $COLLECTION_DIR

# Set env var so ansible --version does not error with getpass.getuser()
export USER=user1

echo "Running 'ansible --version'..."
ansible --version

echo "Running ansible-test sanity on $NAMESPACE-$NAME-$VERSION ..."
# NOTE: skipping some sanity tests
# "import" and "validate-modules" require sandboxing
# "pslint" throws ScriptRequiresMissingModules when container is not run as root
# "ansible-doc" is already called for all plugins in import process
ansible-test sanity --skip-test import --skip-test validate-modules --skip-test pslint --skip-test ansible-doc --color no --failure-ok

echo "ansible-test sanity complete."

EDA_PLUGIN_DIR=$COLLECTION_DIR/extensions/eda/plugins
EDA_PLUGIN_SOURCE=$COLLECTION_DIR/extensions/eda/plugins/event_source
EDA_PLUGIN_FILTER=$COLLECTION_DIR/extensions/eda/plugins/event_filter


if [ -d "$EDA_PLUGIN_DIR" ]
then
    echo "EDA plugin content found. Running ruff on /extensions/eda/plugins..."
    cd /eda/tox
    tox -q -e ruff -- $COLLECTION_DIR

    echo "Running darglint on /extensions/eda/plugins..."
    tox -q -e darglint -- $COLLECTION_DIR

    if [ -d "$EDA_PLUGIN_SOURCE" ]
    then
        echo "Running pylint on /extensions/eda/plugins/event_source..."
        tox -e pylint-event-source -q -- $COLLECTION_DIR
    else
        echo "No EDA event_source plugins found. Skipping pylint on /extensions/eda/plugins/event_source."
    fi

    if [ -d "$EDA_PLUGIN_FILTER" ]
    then
        echo "Running pylint on /extensions/eda/plugins/event_filter..."
        tox -e pylint-event-filter -q -- $COLLECTION_DIR
    else
        echo "No EDA event_filter plugins found. Skipping pylint on /extensions/eda/plugins/event_filter."
    fi
    echo "EDA linting complete."

else
    echo "No EDA content found. Skipping linters."
fi

