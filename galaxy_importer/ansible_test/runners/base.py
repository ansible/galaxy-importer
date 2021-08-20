# (c) 2012-2020, Ansible by Red Hat
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

import abc
import logging

default_logger = logging.getLogger(__name__)


class BaseTestRunner(object):
    """
    :param dir: Dir where collection is extracted, used by local runner.
    :param metadata: Collection metadata, used by local runner.
    :param filepath: Path where archive file is located.
    """

    def __init__(self, dir="", metadata="", file=None, filepath=None, logger=None):
        self.log = logger or default_logger
        self.dir = dir
        self.filepath = filepath
        self.metadata = metadata
        self.file = file

    @abc.abstractmethod
    def run():
        pass
