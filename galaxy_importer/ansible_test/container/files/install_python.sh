#/bin/bash

set -e

if [ ! -d /.pyenv ]; then
    git clone https://github.com/pyenv/pyenv.git /.pyenv
    cd /.pyenv && src/configure && make -C src
fi

rm -rf /tmp/python-build*
export PYENV_ROOT=/.pyenv
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
pyenv install -v $1
alternatives --install /usr/bin/python$1 python$1 /.pyenv/versions/$1.*/bin/python 1
alternatives --install /usr/bin/pip$1 pip$1 /.pyenv/versions/$1.*/bin/python 1
