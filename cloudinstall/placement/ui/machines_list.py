# Copyright 2015 Canonical, Ltd.
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
from urwid import (AttrMap, Divider, Padding, Pile, Text, WidgetWrap)

from cloudinstall.maas import satisfies

from cloudinstall.placement.ui.filter_box import FilterBox
from cloudinstall.placement.ui.machine_widget import MachineWidget

log = logging.getLogger('cloudinstall.placement')


class MachinesList(WidgetWrap):

    """A list of machines with configurable action buttons for each
    machine.

    actions - a list of ('label', function) pairs that wil be used to
    create buttons for each machine.  The machine will be passed to
    the function as userdata.

    constraints - a dict of constraints to filter the machines list.
    only machines matching all the constraints will be shown.

    show_hardware - bool, whether or not to show the hardware details
    for each of the machines

    title_widgets - A Text Widget to be used in place of the default
    title.

    show_assignments - bool, whether or not to show the assignments
    for each of the machines.

    """

    def __init__(self, controller, actions, constraints=None,
                 show_hardware=False, title_widgets=None,
                 show_assignments=True):
        self.controller = controller
        self.actions = actions
        self.machine_widgets = []
        if constraints is None:
            self.constraints = {}
        else:
            self.constraints = constraints
        self.show_hardware = show_hardware
        self.show_assignments = show_assignments
        self.filter_string = ""
        w = self.build_widgets(title_widgets)
        self.update()
        super().__init__(w)

    def selectable(self):
        # overridden to ensure that we can arrow through the buttons
        # shouldn't be necessary according to documented behavior of
        # Pile & Columns, but discovered via trial & error.
        return True

    def build_widgets(self, title_widgets):
        if title_widgets is None:
            if len(self.constraints) > 0:
                cstr = " matching constraints"
            else:
                cstr = ""

            title_widgets = Text("Machines" + cstr, align='center')

        self.filter_edit_box = FilterBox(self.handle_filter_change)

        self.machine_pile = Pile([title_widgets,
                                  Divider(),
                                  self.filter_edit_box] +
                                 self.machine_widgets)
        return self.machine_pile

    def handle_filter_change(self, edit_button, userdata):
        self.filter_string = userdata
        self.update()

    def find_machine_widget(self, m):
        return next((mw for mw in self.machine_widgets if
                     mw.machine.instance_id == m.instance_id), None)

    def update(self):
        machines = self.controller.machines()
        for mw in self.machine_widgets:
            machine = next((m for m in machines if
                            mw.machine.instance_id == m.instance_id), None)
            if machine is None:
                self.remove_machine(mw.machine)

        n_satisfying_machines = len(machines)

        def get_placement_filter_label(d):
            s = ""
            for atype, al in d.items():
                s += " ".join(["{} {}".format(cc.charm_name,
                                              cc.display_name)
                               for cc in al])
            return s

        for m in machines:
            if not satisfies(m, self.constraints)[0]:
                self.remove_machine(m)
                n_satisfying_machines -= 1
                continue

            assignment_names = ""
            ad = self.controller.assignments_for_machine(m)
            assignment_names = get_placement_filter_label(ad)
            dd = self.controller.deployments_for_machine(m)
            deployment_names = get_placement_filter_label(dd)
            filter_label = "{} {} {}".format(m.filter_label(),
                                             assignment_names,
                                             deployment_names)

            if self.filter_string != "" and \
               self.filter_string not in filter_label:
                self.remove_machine(m)
                continue

            mw = self.find_machine_widget(m)

            if mw is None:
                mw = self.add_machine_widget(m)
            mw.update()

        self.filter_edit_box.set_info(len(self.machine_widgets),
                                      n_satisfying_machines)

    def add_machine_widget(self, machine):
        mw = MachineWidget(machine, self.controller, self.actions,
                           self.show_hardware, self.show_assignments)
        self.machine_widgets.append(mw)
        options = self.machine_pile.options()
        self.machine_pile.contents.append((mw, options))

        self.machine_pile.contents.append((AttrMap(Padding(Divider('\u23bc'),
                                                           left=2, right=2),
                                                   'label'), options))
        return mw

    def remove_machine(self, machine):
        mw = self.find_machine_widget(machine)
        if mw is None:
            return

        self.machine_widgets.remove(mw)
        mw_idx = 0
        for w, opts in self.machine_pile.contents:
            if w == mw:
                break
            mw_idx += 1

        c = self.machine_pile.contents[:mw_idx] + \
            self.machine_pile.contents[mw_idx + 2:]
        self.machine_pile.contents = c
