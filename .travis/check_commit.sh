#!/bin/bash

if [ "$TRAVIS_PULL_REQUEST" = 'false' ]; then
  exit 0
fi

git fetch origin "+refs/heads/${TRAVIS_BRANCH}:refs/remotes/origin/${TRAVIS_BRANCH}"

REGEXP="CHANGES\/[0-9]+\.(feature|bugfix|doc|removal|misc)$"
PR_FILES=$(git diff --name-only origin/${TRAVIS_BRANCH})

for file in $PR_FILES; do
  echo $file
  if [[ $file =~ $REGEXP ]]; then
    echo $file IS A MATCH
    CHANGELOG_FOUND=true
  fi
done

if [ "$CHANGELOG_FOUND" != true ];  then
  echo "ERROR: No changelog entry found in CHANGES directory."
  exit 1
fi
