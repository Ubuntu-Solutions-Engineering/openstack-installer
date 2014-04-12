#!/usr/bin/env python3
#
# test_jujustate.py - Unittests for JujuState
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

# import helpers

# load_status = lambda f: helpers.load_status(f, JujuState)

# @load_status('juju-output/no-services.out')
# def test_noservices(s):
#     assert len(s.assignments) == 0
#     assert len(s.services) == 0

# @load_status('juju-output/one-pending.out')
# def test_onepending(s):
#     assert len(s.assignments) == 0
#     assert len(s.services) == 0

# @load_status('juju-output/service-pending.out')
# def test_servicepending(s):
#     assert len(s.assignments) == 1
#     assert len(s.services) == 1

import unittest
import sys
import os
import ipaddress
sys.path.insert(0, '../cloudinstall')
from cloudinstall.utils import _run
from cloudinstall.juju import JujuState

JUJU_USELIVE = os.environ.get('JUJU_USELIVE', 0)
JUJU_INSTALLED = os.path.exists("/usr/bin/juju")

class JujuStateMultiTest(unittest.TestCase):
    def setUp(self):
        self.juju = None
        if JUJU_USELIVE and JUJU_INSTALLED:
            self.juju = JujuState(_run('juju status').decode('ascii'))
        else:
            with open('test/juju-output/juju-status-multi-install.yaml') as f:
                self.juju = JujuState(f.read())

    def test_verify_instance_id(self):
        """ Validate we have maas instance-ids

        Example instance-id:

          /MAAS/api/1.0/nodes/node-a59c35b4-bfed-11e3-b7a8-a0cec8006f97/
        """
        for m in self.juju.machines():
            self.assertTrue('MAAS/api' in m.instance_id)

    def test_machine_dns_names(self):
        """ Are machine dns-names assigned """
        for m in self.juju.machines():
            self.assertTrue(m.dns_name)

    def test_machine_dns_names_host(self):
        """ Machines should have `maas` as the host in their dns-name """
        for m in self.juju.machines():
            self.assertTrue('maas' in m.dns_name)

    def test_container_dns_is_ip(self):
        """ Make sure dns-names are valid ip address """
        for m in self.juju.machines():
            for c in m.containers:
                self.assertTrue(ipaddress.ip_address(c.dns_name))

    def test_container_lxc_instance_id(self):
        """ Container instance ids should have lxc defined """
        for m in self.juju.machines():
            for c in m.containers:
                self.assertTrue('lxc' in c.instance_id)

class JujuStateSingleTest(unittest.TestCase):
    def setUp(self):
        with open('juju-output/juju-status-single-install.yaml') as f:
            self.status_yaml = f.read().decode('ascii')
        self.juju = JujuState(self.status_yaml)
