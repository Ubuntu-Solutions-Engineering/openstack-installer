#!/usr/bin/env python
#
# test_jujuclient.py - Juju Api Tests
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Usage:
# juju bootstrap
# nose test

import unittest
import os
import sys
sys.path.insert(0, '../cloudinstall')

from cloudinstall.juju.client import JujuClient
from cloudinstall.utils import randomString

JUJU_PASS = os.environ['JUJU_PASS'] if os.environ['JUJU_PASS'] else randomString()
JUJU_URL = os.environ['JUJU_URL'] if os.environ['JUJU_URL'] else 'juju-bootstrap.master'
JUJU_INSTALLED = os.path.exists(os.path.join(os.path.expanduser('~'),
                                             '.juju/environments.yaml'))

@unittest.skipIf(not JUJU_INSTALLED, "Juju is not installed")
class JujuClientTest(unittest.TestCase):
    def setUp(self):
        self.c = JujuClient()

    def test_login(self):
        self.c.login(JUJU_PASS)
        self.assertTrue(self.is_connected)

if __name__ == '__main__':
    unittest.main()
