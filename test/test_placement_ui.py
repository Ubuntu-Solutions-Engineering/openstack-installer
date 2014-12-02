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
from cloudinstall.placement.ui import (ServiceWidget)


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


class ServiceWidgetTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()
        self.mock_opts = MagicMock()

        self.pc = PlacementController(self.mock_maas_state,
                                      self.mock_opts)

        def make_fake_machine(name):
            m = MagicMock(name=name)
            pmid = PropertyMock(return_value="fake-iid-{}".format(name))
            type(m).instance_id = pmid
            hnstr = "{}-hostname".format(name)
            pmhostname = PropertyMock(return_value=hnstr)
            type(m).hostname = pmhostname
            return m

        self.mock_machine = make_fake_machine('machine1')
        self.mock_machine_2 = make_fake_machine('machine2')

        self.mock_machines = [self.mock_machine, self.mock_machine_2]

        self.mock_maas_state.machines.return_value = self.mock_machines

    def test_required_label_shown(self):
        """Widget showing a required charm should have a label showing how
        many units are required"""
        w = ServiceWidget(CharmKeystone, self.pc)
        w.update()
        self.assertTrue(search_in_widget("0 of 1 placed", w))

    def test_required_label_not_shown(self):
        """Widget showing a non-required charm should NOT have a label showing
        how many units are required.
        """
        w = ServiceWidget(CharmJujuGui, self.pc)
        w.update()

        self.assertFalse(search_in_widget(".* of .* placed", w))

    def test_show_assignments(self):
        """Widget with show_assignments set should show assignments"""
        w = ServiceWidget(CharmNovaCompute, self.pc, show_assignments=True)
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        log.debug(self.pc.machines_for_charm(CharmNovaCompute))
        w.update()

        self.assertTrue(search_in_widget("LXC.*machine1-hostname", w))

    def test_dont_show_assignments(self):
        """Widget with show_assignments set to FALSE should NOT show
        assignments"""
        w = ServiceWidget(CharmNovaCompute, self.pc, show_assignments=False)
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        log.debug(self.pc.machines_for_charm(CharmNovaCompute))
        w.update()

        self.assertFalse(search_in_widget("LXC.*machine1-hostname", w))

    def test_show_constraints(self):
        """Widget with show_constraints set should show constraints"""
        w = ServiceWidget(CharmNovaCompute, self.pc, show_constraints=True)
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        log.debug(self.pc.machines_for_charm(CharmNovaCompute))
        w.update()

        conpat = ("constraints.*" +
                  ".*".join(CharmNovaCompute.constraints.keys()))

        self.assertTrue(search_in_widget(conpat, w))

    def test_dont_show_constraints(self):
        """Widget with show_constraints set to FALSE should NOT show
        constraints"""
        w = ServiceWidget(CharmNovaCompute, self.pc, show_constraints=False)
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        log.debug(self.pc.machines_for_charm(CharmNovaCompute))
        w.update()

        self.assertFalse(search_in_widget("constraints", w))
