#!/bin/bash

if [[ "$TRAVIS_PULL_REQUEST" != 'false' ]]; then
  pip install requests
  python .travis/custom_check_pull_request.py
fi
