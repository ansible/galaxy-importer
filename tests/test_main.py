# (c) 2012-2019, Ansible by Red Hat
#
# This file is part of Ansible Galaxy
#
# Ansible Galaxy is free software: you can redistribute it and/or modify
# it under the terms of the Apache License as published by
# the Apache Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Ansible Galaxy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Apache License for more details.
#
# You should have received a copy of the Apache License
# along with Galaxy.  If not, see <http://www.apache.org/licenses/>.

import pytest

from galaxy_importer import main


def test_parser():
    parser = main.parse_args(['path/to/my_file.tar.gz'])
    assert parser.file == 'path/to/my_file.tar.gz'
    assert not parser.print_result

    parser = main.parse_args(['my_file.tar.gz', '--print-result'])
    assert parser.file == 'my_file.tar.gz'
    assert parser.print_result

    # SystemExit with missing required positional file argument
    with pytest.raises(SystemExit):
        main.parse_args(['--print-result'])


def test_main_no_args():
    with pytest.raises(SystemExit):
        main.main(args={})
