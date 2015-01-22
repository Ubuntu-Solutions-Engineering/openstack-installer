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
import yaml
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

import cloudinstall.utils as utils
from cloudinstall.config import Config
from cloudinstall.charms.jujugui import CharmJujuGui
from cloudinstall.charms.keystone import CharmKeystone
from cloudinstall.charms.compute import CharmNovaCompute

from cloudinstall.placement.controller import (AssignmentType,
                                               PlacementController)
from cloudinstall.placement.ui import (MachinesList, MachineWidget,
                                       ServicesList, ServiceWidget)


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


def make_fake_machine(name, md=None):
    m = MagicMock(name=name)
    m.instance_id = "fake-iid-{}".format(name)
    m.hostname = "{}-hostname".format(name)
    m.status = "{}-status".format(name)

    if md is None:
        md = {}

    m.machine = md
    m.arch = md.get("arch", "{}-arch".format(name))
    m.cpu_cores = md.get("cpu_count", "{}-cpu_count".format(name))
    m.mem = md.get("mem", "{}-mem".format(name))
    m.storage = md.get("storage", "{}-storage".format(name))
    m.filter_label.return_value = "{}-filter_label".format(name)

    return m


class ServiceWidgetTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()

        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            utils.spew(tempf.name, yaml.dump(dict()))
            self.conf = Config({}, tempf.name)

        self.pc = PlacementController(self.mock_maas_state,
                                      self.conf)

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
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            utils.spew(tempf.name, yaml.dump(dict()))
            self.conf = Config({}, tempf.name)

        self.pc = PlacementController(self.mock_maas_state,
                                      self.conf)
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


@patch('cloudinstall.placement.ui.MachineWidget')
class MachinesListTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            utils.spew(tempf.name, yaml.dump(dict()))
            self.conf = Config({}, tempf.name)

        self.pc = PlacementController(self.mock_maas_state,
                                      self.conf)
        self.mock_machine = make_fake_machine('machine1', {'cpu_count': 3})
        self.mock_machine2 = make_fake_machine('machine2')
        self.mock_machine3 = make_fake_machine('machine3')

        self.mock_machines = [self.mock_machine]

        self.mock_maas_state.machines.return_value = self.mock_machines

        self.actions = []

    def test_widgets_config(self, mock_machinewidget):
        for show_hardware in [False, True]:
            for show_assignments in [False, True]:
                MachinesList(self.pc, self.actions,
                             show_hardware=show_hardware,
                             show_assignments=show_assignments)
                mock_machinewidget.assert_called_with(
                    self.mock_machine,
                    self.pc,
                    self.actions,
                    show_hardware,
                    show_assignments)
                mock_machinewidget.reset_mock()

    def test_show_matching_constraints(self, mock_machinewidget):
        ml = MachinesList(self.pc, self.actions,
                          {'cpu_cores': 2})
        self.assertEqual(1, len(ml.machine_widgets))

    def test_hide_non_matching_constraints(self, mock_machinewidget):
        ml = MachinesList(self.pc, self.actions,
                          {'cpu_cores': 16384})
        self.assertEqual(0, len(ml.machine_widgets))

    def test_show_matching_filter(self, mock_machinewidget):
        self.mock_maas_state.machines.return_value = [self.mock_machine,
                                                      self.mock_machine2,
                                                      self.mock_machine3]
        # a little extra work to ensure that calls to
        # MockWidget.__init__() return mocks with the intended machine
        # attribute set:
        mw1 = MagicMock(name="mw1")
        mw1.machine = self.mock_machine
        mw2 = MagicMock(name="mw2")
        mw2.machine = self.mock_machine2
        mw3 = MagicMock(name="mw3")
        mw3.machine = self.mock_machine3
        mock_machinewidget.side_effect = [mw1, mw2, mw3]

        ml = MachinesList(self.pc, self.actions)
        self.assertEqual(3, len(ml.machine_widgets))

        ml.filter_string = "machine1-filter_label"
        ml.update()
        self.assertEqual(1, len(ml.machine_widgets))


@patch('cloudinstall.placement.ui.ServiceWidget')
class ServicesListTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            utils.spew(tempf.name, yaml.dump(dict()))
            self.conf = Config({}, tempf.name)

        self.pc = PlacementController(self.mock_maas_state,
                                      self.conf)
        self.mock_machine = make_fake_machine('machine1', {'cpu_count': 3})
        self.mock_machine2 = make_fake_machine('machine2')
        self.mock_machine3 = make_fake_machine('machine3')

        self.mock_machines = [self.mock_machine]

        self.mock_maas_state.machines.return_value = self.mock_machines

        self.actions = []

    def test_widgets_config(self, mock_servicewidgetclass):
        for show_constraints in [False, True]:
            ServicesList(self.pc, self.actions,
                         show_constraints=show_constraints)

            mock_servicewidgetclass.assert_any_call(
                CharmNovaCompute,
                self.pc,
                self.actions,
                show_constraints)
            mock_servicewidgetclass.reset_mock()

    def test_no_machine_no_constraints(self, mock_servicewidgetclass):
        with patch.object(self.pc, 'charm_classes') as mock_classesfunc:
            fc = MagicMock(name='fakeclass1')
            fc.required_num_units.return_value = 1
            fc.constraints = {'cpu_count': 1000}
            mock_classesfunc.return_value = [fc]
            sl = ServicesList(self.pc, self.actions)
            self.assertEqual(len(sl.service_widgets), 1)

    def test_machine_checks_constraints(self, mock_servicewidgetclass):
        mock_machine = make_fake_machine('fm', {'cpu_count': 0,
                                                'storage': 0,
                                                'memory': 0})
        sl = ServicesList(self.pc, self.actions, machine=mock_machine)
        self.assertEqual(len(sl.service_widgets), 0)

    def test_do_not_show_assigned(self, mock_servicewidgetclass):
        mock_machine = make_fake_machine('fm', {'cpu_count': 0,
                                                'storage': 0,
                                                'memory': 0})
        self.pc.assign(mock_machine, CharmNovaCompute,
                       AssignmentType.LXC)
        sl = ServicesList(self.pc, self.actions, machine=mock_machine)
        classes = [sw.charm_class for sw in sl.service_widgets]
        self.assertTrue(CharmNovaCompute not in classes)

    def test_show_type(self, mock_servicewidgetclass):
        """Test combinations of show_type values.

        This tests three values of show_type with three return values
        for is_required(): all required, no required, and 1/3
        required. It's all lumped in one test to consolidate setup.

        """
        mock_sw1 = MagicMock(name='sw1')
        mock_sw1.charm_class.charm_name = 'cc1'
        mock_sw2 = MagicMock(name='sw2')
        mock_sw2.charm_class.charm_name = 'cc2'
        mock_sw3 = MagicMock(name='sw3')
        mock_sw3.charm_class.charm_name = 'cc3'
        mock_servicewidgetclass.side_effect = [mock_sw1, mock_sw2,
                                               mock_sw3]

        with patch.object(self.pc, 'service_is_required') as mock_isreq:
            with patch.object(self.pc, 'charm_classes') as mock_classesfunc:
                mock_classesfunc.return_value = [MagicMock(name='fake-class-1',
                                                           charm_name='cc1'),
                                                 MagicMock(name='fake-class-2',
                                                           charm_name='cc2'),
                                                 MagicMock(name='fake-class-3',
                                                           charm_name='cc3')]

                # First, test when all charms are required
                mock_isreq.return_value = True

                # rsl shows required charms
                rsl = ServicesList(self.pc, self.actions, machine=None,
                                   show_type='required')
                self.assertEqual(len(mock_isreq.mock_calls), 3)
                # should show all 3
                self.assertEqual(len(rsl.service_widgets), 3)

                mock_isreq.reset_mock()
                mock_servicewidgetclass.reset_mock()
                mock_servicewidgetclass.side_effect = [mock_sw1, mock_sw2,
                                                       mock_sw3]

                # usl shows ONLY un-required charms
                usl = ServicesList(self.pc, self.actions, machine=None,
                                   show_type='non-required')
                self.assertEqual(len(mock_isreq.mock_calls), 3)
                # should show 0
                self.assertEqual(len(usl.service_widgets), 0)

                mock_isreq.reset_mock()
                mock_servicewidgetclass.reset_mock()
                mock_servicewidgetclass.side_effect = [mock_sw1, mock_sw2,
                                                       mock_sw3]

                # asl has default show_type='all', showing all charms
                asl = ServicesList(self.pc, self.actions)
                self.assertEqual(len(mock_isreq.mock_calls), 3)
                # should show all 3
                self.assertEqual(len(asl.service_widgets), 3)

                mock_isreq.reset_mock()
                mock_servicewidgetclass.reset_mock()
                mock_servicewidgetclass.side_effect = [mock_sw1, mock_sw2,
                                                       mock_sw3]

                # next, test where no charms are required
                mock_isreq.return_value = False
                rsl.update()
                self.assertEqual(len(mock_isreq.mock_calls), 3)
                # should show 0 charms
                self.assertEqual(len(rsl.service_widgets), 0)

                mock_isreq.reset_mock()
                mock_servicewidgetclass.reset_mock()
                mock_servicewidgetclass.side_effect = [mock_sw1, mock_sw2,
                                                       mock_sw3]

                usl.update()
                self.assertEqual(len(mock_isreq.mock_calls), 3)
                # should show all 3
                self.assertEqual(len(usl.service_widgets), 3)

                mock_isreq.reset_mock()
                mock_servicewidgetclass.reset_mock()
                mock_servicewidgetclass.side_effect = [mock_sw1, mock_sw2,
                                                       mock_sw3]

                asl.update()
                self.assertEqual(len(mock_isreq.mock_calls), 3)
                # should still show all 3
                self.assertEqual(len(asl.service_widgets), 3)
                mock_isreq.reset_mock()
                mock_servicewidgetclass.reset_mock()
                mock_servicewidgetclass.side_effect = [mock_sw1, mock_sw2,
                                                       mock_sw3]

                # next test two un-required and one required charm:
                mock_isreq.side_effect = [False, True, False]
                rsl.update()
                self.assertEqual(len(mock_isreq.mock_calls), 3)
                # should show 1:
                self.assertEqual(len(rsl.service_widgets), 1)

                mock_isreq.reset_mock()
                mock_servicewidgetclass.reset_mock()
                mock_servicewidgetclass.side_effect = [mock_sw1, mock_sw2,
                                                       mock_sw3]
                mock_isreq.side_effect = [False, True, False]

                usl.update()
                self.assertEqual(len(mock_isreq.mock_calls), 3)
                # should show two
                self.assertEqual(len(usl.service_widgets), 2)

                mock_isreq.reset_mock()
                mock_servicewidgetclass.reset_mock()
                mock_servicewidgetclass.side_effect = [mock_sw1, mock_sw2,
                                                       mock_sw3]
                mock_isreq.side_effect = [False, True, False]

                asl.update()
                self.assertEqual(len(mock_isreq.mock_calls), 3)
                # should still show all three
                self.assertEqual(len(asl.service_widgets), 3)
