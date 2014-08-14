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
import yaml

from cloudinstall.maas import MaasMachine, MaasMachineStatus, MaasState

DATA_DIR = os.path.join(os.path.dirname(__file__), 'maas-output')


class MaasMachineTestCase(unittest.TestCase):

    def setUp(self):
        self.empty_machine = MaasMachine(-1, {})

        onedeclared = yaml.load(open(os.path.join(DATA_DIR,
                                                  'bootstrap+1declared.yaml')))
        self.m_declared = MaasMachine(-1, onedeclared[1])

        oneready = yaml.load(open(os.path.join(DATA_DIR,
                                               'bootstrap+1ready.yaml')))
        self.m_ready = MaasMachine(-1, oneready[1])

    def test_empty_machine_unknonw_status(self):
        self.assertEqual(self.empty_machine.status, MaasMachineStatus.UNKNOWN)

    def test_declared_state(self):
        self.assertEqual(self.m_declared.status, MaasMachineStatus.DECLARED)

    def test_ready_state(self):
        self.assertEqual(self.m_ready.status, MaasMachineStatus.READY)


class MaasStateTestCase(unittest.TestCase):
    def setUp(self):
        bootstrap_only = yaml.load(open(os.path.join(DATA_DIR,
                                                     'bootstrap-only.yaml')))
        self.mock_client_bootstrap_only = MagicMock()
        p = PropertyMock(return_value=bootstrap_only)
        type(self.mock_client_bootstrap_only).nodes = p

        onedeclared = yaml.load(open(os.path.join(DATA_DIR,
                                                  'bootstrap+1declared.yaml')))
        self.mock_client_onedeclared = MagicMock()
        p = PropertyMock(return_value=onedeclared)
        type(self.mock_client_onedeclared).nodes = p

        oneready = yaml.load(open(os.path.join(DATA_DIR,
                                               'bootstrap+1ready.yaml')))
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
