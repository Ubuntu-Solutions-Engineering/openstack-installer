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

from collections import defaultdict
import logging

import pprint

from urwid import (Button, Columns, Divider, Filler,
                   Padding, Pile, Text, WidgetWrap)

from cloudinstall.utils import load_charms

log = logging.getLogger('cloudinstall.placement')


class PlaceholderMachine:
    """A dummy machine that doesn't map to an existing maas machine"""

    def __init__(self, instance_id, name):
        self.instance_id = instance_id
        self.name = name        # TODO name or display_name or what?

    def __repr__(self):
        return "<Placeholder Machine: {}>".format(self.name)


class PlacementController:
    """Keeps state of current machines and their assigned services.
    """

    def __init__(self, maas_state):
        self.maas_state = maas_state
        self.assignments = defaultdict(list)  # instance_id -> [charm class]
        self.first_available = PlaceholderMachine("first-available",
                                                  "First Available")

    def machines(self):
        return [self.first_available] + self.maas_state.machines()

    def charm_classes(self):
        return [m.__charm_class__ for m in load_charms()
                if not m.__charm_class__.disabled]

    def assign(self, instance_id, charm_class):
        for m, l in self.assignments.items():
            if charm_class in l:
                l.remove(charm_class)
        self.assignments[instance_id] = charm_class

    def machine_for_charm(self, charm_class):
        machines = self.machines()
        for m_id, l in self.assignments.items():
            if charm_class in l:
                return next((m for m in machines
                             if m.instance_id == m_id), None)
        return None

    def assignments_for_machine(self, m):
        return self.assignments[m.instance_id]

    def set_all_assignments(self, assignments):
        self.assignments = assignments

    def gen_defaults(self):
        assignments = defaultdict(list)

        maas_machines = self.maas_state.machines()

        def machine_or_first_avail(index):
            if len(maas_machines) > index:
                return maas_machines[index]
            else:
                return self.first_available

        cur_machine = 0
        m_controller = machine_or_first_avail(cur_machine)
        cur_machine += 1

        for charm_class in self.charm_classes():

            if charm_class.isolate:
                machine = machine_or_first_avail(cur_machine)
                cur_machine += 1
                assignments[machine.instance_id].append(charm_class)
            else:
                assignments[m_controller.instance_id].append(charm_class)

        log.debug("Assignments generated: " + pprint.pformat(assignments))
        return assignments


class PlacementView(WidgetWrap):
    """Handles display of machines and services.
    """

    def __init__(self, controller):
        self.controller = controller
        w = self.build_widgets()
        super().__init__(w)

    def scroll_down(self):
        pass

    def scroll_up(self):
        pass

    def build_widgets(self):
        self.machine_list = Pile([Text("Machines")] +
                                 self.machine_widgets())

        self.service_list = Pile([Text("Services")] +
                                 self.service_widgets())
        self.info_pane = Pile([Text("Info?")])

        cols = Columns([self.machine_list,
                        self.service_list,
                        self.info_pane])

        return Filler(cols, valign='top')

    def machine_widgets(self):
        mw = []
        for m in self.controller.machines():
            mw += [Padding(self.widget_for_machine(m),
                           min_width=24,
                           left=2, right=2),
                   Button("change"),
                   Divider()]
        return mw

    def widget_for_machine(self, machine):
        assignments = self.controller.assignments_for_machine(machine)

        astr = 'assignments: ' + ', '.join([c.display_name for c in
                                            assignments])

        return Pile([Text(repr(machine)),
                     Text(astr)])

    def service_widgets(self):
        sw = []
        for cc in self.controller.charm_classes():
            sw += [Padding(self.widget_for_charm_class(cc),
                           min_width=24,
                           left=2, right=2),
                   Button("change"),
                   Divider()]
        return sw

    def widget_for_charm_class(self, cc):
        m = self.controller.machine_for_charm(cc)
        return Pile([Text(cc.display_name),
                     Text(repr(m))])
