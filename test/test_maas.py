#!/usr/bin/env python
#
# tests maas/__init__.py
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

import os
import unittest
from unittest.mock import MagicMock, PropertyMock
import json

from cloudinstall.maas import (MaasMachine, MaasMachineStatus, MaasState,
                               satisfies)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'maas-output')


class SatisfiesTestCase(unittest.TestCase):
    def setUp(self):
        m1d = {'cpu_count': 2,
               'storage': 20,
               'memory': 2048,
               'architecture': 'amd64'}
        self.machine1 = MaasMachine('m1id', m1d)
        m2d = {'cpu_count': '*',
               'storage': '*',
               'memory': '*',
               'architecture': '*'}
        self.machine2 = MaasMachine('m2id', m2d)

    def _do_test(self, cons, nfailures, machine=None):
        if not machine:
            machine = self.machine1
        sat, failures = satisfies(machine, cons)
        self.assertEqual(sat, nfailures == 0)
        self.assertEqual(len(failures), nfailures)

    def test_satisfies_empty(self):
        self._do_test(dict(), 0)

    def test_satisfies_some(self):
        self._do_test(dict(storage=15, arch='amd64'), 0)

    def test_satisfies_nomatch(self):
        self._do_test(dict(storage=15, arch='ENIAC'), 1)

    def test_satisfies_insufficient(self):
        self._do_test(dict(storage=100000000), 1)

    def test_satisfies_multifail(self):
        self._do_test({'cpu_cores': 20, 'arch': 'ENIAC'}, 2)

    def test_handles_units_sufficient(self):
        self._do_test(dict(mem='2G'), 0)

    def test_handles_units_insufficient(self):
        self._do_test(dict(mem='64G'), 1)

    def test_asterisk_satisfies_all(self):
        self._do_test(dict(mem='64G'), 0, machine=self.machine2)
        self._do_test(dict(storage='64G'), 0, machine=self.machine2)
        self._do_test(dict(arch='ENIAC'), 0, machine=self.machine2)


class MaasMachineTestCase(unittest.TestCase):

    def setUp(self):
        self.empty_machine = MaasMachine(-1, {})

        onedeclared = json.load(open(os.path.join(DATA_DIR,
                                                  'bootstrap+1declared.json')))
        self.m_declared = MaasMachine(-1, onedeclared[1])

        oneready = json.load(open(os.path.join(DATA_DIR,
                                               'bootstrap+1ready.json')))
        self.m_ready = MaasMachine(-1, oneready[1])

    def test_empty_machine_unknown_status(self):
        self.assertEqual(self.empty_machine.status, MaasMachineStatus.UNKNOWN)

    def test_new_state(self):
        self.assertEqual(self.m_declared.status, MaasMachineStatus.NEW)

    def test_ready_state(self):
        self.assertEqual(self.m_ready.status, MaasMachineStatus.READY)


class MaasMachineStatusTestCase(unittest.TestCase):
    """MaasMachine should use the same labels as MAAS 1.7"""

    def test_statuses(self):
        labels = ['new', 'commissioning', 'failed_commissioning',
                  'missing', 'ready', 'reserved', 'deployed',
                  'retired', 'broken', 'deploying', 'maas_1_7_allocated',
                  'failed_deployment', 'releasing',
                  'failed_releasing', 'disk_erasing',
                  'failed_disk_erasing']

        for i in range(len(labels)):
            d = dict(status=i)
            m = MaasMachine('fakeid', d)
            self.assertEqual(str(m.status), labels[i])

    def test_allocated_folding_works(self):
        """Maas 1.7 added states but maps several to #6, which was previously
        'ALLOCATED'. Test that we can correctly map these to ALLOCATED too"""

        self.assertEqual(MaasMachineStatus(6), MaasMachineStatus.ALLOCATED)


class MaasStateTestCase(unittest.TestCase):
    def setUp(self):
        bootstrap_only = json.load(open(os.path.join(DATA_DIR,
                                                     'bootstrap-only.json')))
        self.mock_client_bootstrap_only = MagicMock()
        p = PropertyMock(return_value=bootstrap_only)
        type(self.mock_client_bootstrap_only).nodes = p

        onedeclared = json.load(open(os.path.join(DATA_DIR,
                                                  'bootstrap+1declared.json')))
        self.mock_client_onedeclared = MagicMock()
        p = PropertyMock(return_value=onedeclared)
        type(self.mock_client_onedeclared).nodes = p

        oneready = json.load(open(os.path.join(DATA_DIR,
                                               'bootstrap+1ready.json')))
        self.mock_client_oneready = MagicMock()
        p = PropertyMock(return_value=oneready)
        type(self.mock_client_oneready).nodes = p

    def test_get_machines_no_ready(self):
        s = MaasState(self.mock_client_bootstrap_only)
        all_machines = s.machines()
        self.assertEqual(all_machines, [])

        ready_machines = s.machines(MaasMachineStatus.READY)
        self.assertEqual(ready_machines, [])

        s2 = MaasState(self.mock_client_onedeclared)
        all_machines = s2.machines()
        self.assertEqual(len(all_machines), 1)

        ready_machines = s2.machines(MaasMachineStatus.READY)
        self.assertEqual(ready_machines, [])

    def test_get_machines_one_ready(self):
        s = MaasState(self.mock_client_oneready)
        ready_machines = s.machines(MaasMachineStatus.READY)
        self.assertEqual(len(ready_machines), 1)
