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
    "Read the 'juju status' yaml for single post-install"

    def setUp(self):
        with open('test/juju-output/juju-status-single-install.yaml') as f:
            self.juju = JujuState(f.read())

        self.m_one = self.juju.machine("1")
        self.c_one = self.m_one.container("1/lxc/0")

    def test_ignore_bootstrap_node(self):
        "jujustate.machines() should not include #0"
        self.assertEqual(len(list(self.juju.machines())), 2)

    def test_services(self):
        "All services parsed correctly"
        expected = ['glance', 'juju-gui', 'keystone', 'mysql',
                    'nova-cloud-controller', 'nova-compute',
                    'openstack-dashboard', 'rabbitmq-server']
        actual = list(self.juju.services)
        actual_names = [s.service_name for s in actual]
        self.assertEqual(set(actual_names), set(expected))

    def test_find_service(self):
        "Find a service based on charm name"
        cn = "juju-gui"
        s = self.juju.service(cn)
        self.assertEqual(cn, s.service_name)

    def test_bogus_service_returns_none(self):
        "return empty dictionary for nonexistent services"
        cn = "fake-bogus-charm"
        s = self.juju.service(cn)
        self.assertEqual({}, s.service)

    def test_two_machines_allocated(self):
        ml = self.juju.machines_allocated()
        self.assertEqual(2, len(ml))

    def test_m_one_containers(self):
        cl = list(self.m_one.containers)
        self.assertEqual(7, len(cl))
        self.assertEqual(self.c_one.agent_state, "started")

    def test_get_hardware(self):
        cpu_cores = self.m_one.hardware("cpu-cores")
        self.assertEqual(cpu_cores, '3')
        self.assertEqual(self.c_one.hardware("arch"), "amd64")


class JujuStateSinglePredeployTest(unittest.TestCase):
    "Read the 'juju status' yaml for single pre-deploy"

    def setUp(self):
        with open('test/juju-output/juju-status-single-pre-deploy.yaml') as f:
            self.juju = JujuState(f.read())

    def test_one_machine_allocated(self):
        ml = self.juju.machines_allocated()
        self.assertEqual(1, len(ml))

    def test_no_services(self):
        sl = list(self.juju.services)
        self.assertEqual(0, len(sl))

    def test_no_containers(self):
        m_one = self.juju.machines_allocated()[0]
        cl = list(m_one.containers)
        self.assertEqual(0, len(cl))
