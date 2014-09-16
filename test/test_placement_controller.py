#!/usr/bin/env python
#
# tests placement/controller.py
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

import logging
import os
import unittest
from unittest.mock import MagicMock, PropertyMock

from cloudinstall.charms.keystone import CharmKeystone
from cloudinstall.charms.compute import CharmNovaCompute

from cloudinstall.placement.controller import (AssignmentType,
                                               PlacementController)


DATA_DIR = os.path.join(os.path.dirname(__file__), 'maas-output')

log = logging.getLogger('cloudinstall.test_placement_controller')


class PlacementControllerTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()
        self.mock_opts = MagicMock()
        swopt = PropertyMock(return_value=False)
        type(self.mock_opts).enable_swift = swopt

        self.pc = PlacementController(self.mock_maas_state,
                                      self.mock_opts)
        self.mock_machine = MagicMock(name='machine1')
        pmid = PropertyMock(return_value='fake-instance-id-1')
        type(self.mock_machine).instance_id = pmid

        self.mock_machine_2 = MagicMock(name='machine2')
        pmid2 = PropertyMock(return_value='fake-instance-id-2')
        type(self.mock_machine_2).instance_id = pmid2

        self.mock_machines = [self.mock_machine, self.mock_machine_2]

        self.mock_maas_state.machines.return_value = self.mock_machines

    def _do_test_simple_assign_type(self, assignment_type):
        self.pc.assign(self.mock_machine, CharmNovaCompute, assignment_type)
        print("assignments is {}".format(self.pc.assignments))
        machines = self.pc.machines_for_charm(CharmNovaCompute)
        print('machines fo charm is {}'.format(machines))
        self.assertEqual(machines,
                         {assignment_type: [self.mock_machine]})

        ma = self.pc.assignments_for_machine(self.mock_machine)

        self.assertEqual(ma[assignment_type], [CharmNovaCompute])

    def test_simple_assign_bare(self):
        self._do_test_simple_assign_type(AssignmentType.BareMetal)

    def test_simple_assign_lxc(self):
        self._do_test_simple_assign_type(AssignmentType.LXC)

    def test_simple_assign_kvm(self):
        self._do_test_simple_assign_type(AssignmentType.KVM)

    def test_assign_nonmulti(self):
        self.pc.assign(self.mock_machine, CharmKeystone, AssignmentType.LXC)
        self.assertEqual(self.pc.machines_for_charm(CharmKeystone),
                         {AssignmentType.LXC: [self.mock_machine]})

        self.pc.assign(self.mock_machine, CharmKeystone, AssignmentType.KVM)
        self.assertEqual(self.pc.machines_for_charm(CharmKeystone),
                         {AssignmentType.KVM: [self.mock_machine]})

        am = self.pc.assignments_for_machine(self.mock_machine)
        self.assertEqual(am[AssignmentType.KVM], [CharmKeystone])
        self.assertEqual(am[AssignmentType.LXC], [])

    def test_assign_multi(self):
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        self.assertEqual(self.pc.machines_for_charm(CharmNovaCompute),
                         {AssignmentType.LXC: [self.mock_machine]})

        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.KVM)
        self.assertEqual(self.pc.machines_for_charm(CharmNovaCompute),
                         {AssignmentType.LXC: [self.mock_machine],
                          AssignmentType.KVM: [self.mock_machine]})

        ma = self.pc.assignments_for_machine(self.mock_machine)
        self.assertEqual(ma[AssignmentType.LXC], [CharmNovaCompute])
        self.assertEqual(ma[AssignmentType.KVM], [CharmNovaCompute])

    def test_remove_assignment_multi(self):
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        self.pc.assign(self.mock_machine_2, CharmNovaCompute,
                       AssignmentType.LXC)

        mfc = self.pc.machines_for_charm(CharmNovaCompute)

        mfc_lxc = set(mfc[AssignmentType.LXC])
        self.assertEqual(mfc_lxc, set(self.mock_machines))

        self.pc.clear_assignments(self.mock_machine)
        self.assertEqual(self.pc.machines_for_charm(CharmNovaCompute),
                         {AssignmentType.LXC: [self.mock_machine_2]})
