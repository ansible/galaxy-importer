# (c) 2012-2022, Ansible by Red Hat
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
from packaging.specifiers import InvalidSpecifier

from galaxy_importer.utils import requires_ansible_version


def test_invalid_specifier():
    bad_spec = "37"
    with pytest.raises(InvalidSpecifier):
        requires_ansible_version.validate(bad_spec)


def test_valid_specifier():
    spec = "<2.0"
    result = requires_ansible_version.validate(spec)
    assert result is True, "%s should be a valid requires_ansible specifier but is not" % spec
