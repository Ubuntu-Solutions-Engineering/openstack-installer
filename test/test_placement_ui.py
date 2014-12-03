#!/usr/bin/env python
#
# tests placement/ui.py
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
import re
import unittest
from unittest.mock import MagicMock, PropertyMock

from cloudinstall.charms.jujugui import CharmJujuGui
from cloudinstall.charms.keystone import CharmKeystone
from cloudinstall.charms.compute import CharmNovaCompute

from cloudinstall.placement.controller import (AssignmentType,
                                               PlacementController)
from cloudinstall.placement.ui import (MachineWidget, ServiceWidget)


log = logging.getLogger('cloudinstall.test_placement_ui')


def search_in_widget(pat, w):
    """Helper function to render a widget and check for a regex"""
    canvas = w.render((100,))
    all_lines = " ".join([t.decode() for t in canvas.text])
    matches = re.search(pat, all_lines)
    log.debug("search_in_widget({}, {}):\n"
              "all_lines is: {}\n"
              "matches is {}".format(pat, w, all_lines, matches))
    return matches is not None


def make_fake_machine(name):
    m = MagicMock(name=name)
    pmid = PropertyMock(return_value="fake-iid-{}".format(name))
    type(m).instance_id = pmid
    hnstr = "{}-hostname".format(name)
    pmhostname = PropertyMock(return_value=hnstr)
    type(m).hostname = pmhostname
    pmstatus = PropertyMock(return_value="{}-status".format(name))
    type(m).status = pmstatus
    pmarch = PropertyMock(return_value="{}-arch".format(name))
    type(m).arch = pmarch
    pmcores = PropertyMock(return_value="{}-cores".format(name))
    type(m).cpu_cores = pmcores
    pmmem = PropertyMock(return_value="{}-mem".format(name))
    type(m).mem = pmmem
    pmstorage = PropertyMock(return_value="{}-storage".format(name))
    type(m).storage = pmstorage
    return m


class ServiceWidgetTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()
        self.mock_opts = MagicMock()

        self.pc = PlacementController(self.mock_maas_state,
                                      self.mock_opts)

        self.mock_machine = make_fake_machine('machine1')
        self.mock_machine_2 = make_fake_machine('machine2')

        self.mock_machines = [self.mock_machine, self.mock_machine_2]

        self.mock_maas_state.machines.return_value = self.mock_machines

    def test_required_label_shown(self):
        """Widget showing a required charm should have a label showing how
        many units are required"""
        w = ServiceWidget(CharmKeystone, self.pc)

        self.assertTrue(search_in_widget("0 of 1 placed", w))

    def test_required_label_not_shown(self):
        """Widget showing a non-required charm should NOT have a label showing
        how many units are required.
        """
        w = ServiceWidget(CharmJujuGui, self.pc)

        self.assertFalse(search_in_widget(".* of .* placed", w))

    def test_show_assignments(self):
        """Widget with show_assignments set should show assignments"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = ServiceWidget(CharmNovaCompute, self.pc, show_assignments=True)

        self.assertTrue(search_in_widget("LXC.*machine1-hostname", w))

    def test_dont_show_assignments(self):
        """Widget with show_assignments set to FALSE should NOT show
        assignments"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = ServiceWidget(CharmNovaCompute, self.pc, show_assignments=False)

        self.assertFalse(search_in_widget("LXC.*machine1-hostname", w))

    def test_show_constraints(self):
        """Widget with show_constraints set should show constraints"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = ServiceWidget(CharmNovaCompute, self.pc, show_constraints=True)

        conpat = ("constraints.*" +
                  ".*".join(CharmNovaCompute.constraints.keys()))

        self.assertTrue(search_in_widget(conpat, w))

    def test_dont_show_constraints(self):
        """Widget with show_constraints set to FALSE should NOT show
        constraints"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = ServiceWidget(CharmNovaCompute, self.pc, show_constraints=False)
        self.assertFalse(search_in_widget("constraints", w))

    def test_show_actions(self):
        """Actions should be shown as buttons"""
        fake_action_func = MagicMock()
        actions = [("fake-action", fake_action_func)]
        w = ServiceWidget(CharmNovaCompute, self.pc, actions=actions)
        self.assertTrue(search_in_widget("fake-action", w))

    def test_actions_use_pred(self):
        """Action predicates control whether a button appears (disabled)"""

        # NOTE: this test assumes that disabled buttons are just the
        # button label with parentheses.

        fake_action_func = MagicMock()
        fake_pred = MagicMock()
        fake_pred.return_value = False
        actions = [(fake_pred, "fake-action", fake_action_func)]
        w = ServiceWidget(CharmNovaCompute, self.pc, actions=actions)

        self.assertTrue(search_in_widget("\(.*fake-action.*\)", w))
        fake_pred.assert_called_with(CharmNovaCompute)

        fake_pred.return_value = True
        fake_pred.reset_mock()

        w.update()
        self.assertTrue(search_in_widget("<.*fake-action.*>", w))
        fake_pred.assert_called_with(CharmNovaCompute)


class MachineWidgetTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()
        self.mock_opts = MagicMock()

        self.pc = PlacementController(self.mock_maas_state,
                                      self.mock_opts)
        self.mock_machine = make_fake_machine('machine1')

        self.mock_machines = [self.mock_machine]

        self.mock_maas_state.machines.return_value = self.mock_machines

    def test_hardware_shown(self):
        """show_hardware=True should show hardware details"""
        w = MachineWidget(self.mock_machine, self.pc, show_hardware=True)
        self.assertTrue(search_in_widget("arch", w))
        self.assertTrue(search_in_widget("cores", w))
        self.assertTrue(search_in_widget("mem", w))
        self.assertTrue(search_in_widget("storage", w))

    def test_hardware_not_shown(self):
        """show_hardware=False should NOT show hardware details"""
        w = MachineWidget(self.mock_machine, self.pc, show_hardware=False)
        self.assertFalse(search_in_widget("arch", w))
        self.assertFalse(search_in_widget("cores", w))
        self.assertFalse(search_in_widget("mem", w))
        self.assertFalse(search_in_widget("storage", w))

    def test_show_assignments(self):
        """Widget with show_assignments set should show assignments"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = MachineWidget(self.mock_machine, self.pc, show_assignments=True)

        self.assertTrue(search_in_widget("LXC.*Compute", w))

    def test_dont_show_assignments(self):
        """Widget with show_assignments set to FALSE should NOT show
        assignments"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = MachineWidget(self.mock_machine, self.pc, show_assignments=False)

        self.assertFalse(search_in_widget("LXC.*Compute", w))

    def test_show_actions(self):
        """Actions passed as 2-tuples should always be shown as buttons"""
        fake_action_func = MagicMock()
        actions = [("fake-action", fake_action_func)]
        w = MachineWidget(self.mock_machine, self.pc, actions=actions)
        self.assertTrue(search_in_widget("fake-action", w))

    def test_actions_use_pred(self):
        """Action predicates control whether a button appears (disabled)"""

        # NOTE: this test assumes that disabled buttons are just the
        # button label with parentheses.

        fake_action_func = MagicMock()
        fake_pred = MagicMock()
        fake_pred.return_value = False
        actions = [(fake_pred, "fake-action", fake_action_func)]
        w = MachineWidget(self.mock_machine, self.pc, actions=actions)

        self.assertTrue(search_in_widget("\(.*fake-action.*\)", w))
        fake_pred.assert_called_with(self.mock_machine)

        fake_pred.return_value = True
        fake_pred.reset_mock()

        w.update()
        self.assertTrue(search_in_widget("<.*fake-action.*>", w))
        fake_pred.assert_called_with(self.mock_machine)
