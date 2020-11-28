#!/bin/bash

pip install requests

for sha in $(curl $GITHUB_PR_COMMITS_URL | jq '.[].sha' | sed 's/"//g')
do
  python .github/scripts/custom_check_pull_request.py $sha
done

