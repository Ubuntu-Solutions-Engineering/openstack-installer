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

from urwid import (Button, Columns, Divider, Filler, GridFlow, LineBox,
                   Overlay, Padding, Pile, Text, WidgetWrap)

from cloudinstall.utils import load_charms

log = logging.getLogger('cloudinstall.placement')

BUTTON_SIZE = 20


class PlaceholderMachine:
    """A dummy machine that doesn't map to an existing maas machine"""

    def __init__(self, instance_id, name):
        self.instance_id = instance_id
        self.display_name = name
        self.constraints = defaultdict(lambda: '-')

    @property
    def arch(self):
        return self.constraints['arch']

    @property
    def cpu_cores(self):
        return self.constraints['cpu_cores']

    @property
    def mem(self):
        return self.constraints['mem']

    @property
    def storage(self):
        return self.constraints['storage']

    @property
    def hostname(self):
        return self.display_name

    def matches(self, constraints):
        return True             # TODO

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
        if not charm_class.allow_multi_units:
            for m, l in self.assignments.items():
                if charm_class in l:
                    l.remove(charm_class)
        self.assignments[instance_id].append(charm_class)

    def machines_for_charm(self, charm_class):
        all_machines = self.machines()
        machines = []
        for m_id, assignment_list in self.assignments.items():
            if charm_class in assignment_list:
                m = next((m for m in all_machines
                          if m.instance_id == m_id), None)
                machines.append(m)
        return machines

    def remove_assignment(self, m, cc):
        assignments = self.assignments[m.instance_id]
        assignments.remove(cc)

    def clear_assignments(self, m):
        del self.assignments[m.instance_id]

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


class MachineWidget(WidgetWrap):
    def __init__(self, machine, controller, actions=None,
                 show_hardware=False):
        self.machine = machine
        self.controller = controller
        if actions is None:
            self.actions = []
        else:
            self.actions = actions
        self.show_hardware = show_hardware
        w = self.build_widgets()
        self.update()
        super().__init__(w)

    def hardware_info_markup(self):
        m = self.machine
        return [('label', 'arch'), ' {}  '.format(m.arch),
                ('label', 'cores'), ' {}  '.format(m.cpu_cores),
                ('label', 'mem'), ' {}  '.format(m.mem),
                ('label', 'storage'), ' {}'.format(m.storage)]

    def build_widgets(self):
        self.machine_info_widget = Text("\N{TAPE DRIVE} {}".format(
            self.machine.hostname))
        self.assignments_widget = Text("")

        self.hardware_widget = Text(self.hardware_info_markup())

        buttons = []
        for label, func in self.actions:
            b = Button(label, on_press=func, user_data=self.machine)
            buttons.append(b)

        button_grid = GridFlow(buttons, BUTTON_SIZE, 1, 1, 'right')

        pl = [self.machine_info_widget, self.assignments_widget]
        if self.show_hardware:
            pl.append(self.hardware_widget)
        pl.append(button_grid)

        p = Pile(pl)

        return Padding(p, left=2, right=2)

    def update(self):
        al = self.controller.assignments_for_machine(self.machine)
        astr = "  "
        if len(al) == 0:
            astr += "\N{EMPTY SET}"
        else:
            astr += ", ".join(["\N{GEAR} {}".format(c.display_name)
                               for c in al])

        self.assignments_widget.set_text(astr)


class ServiceWidget(WidgetWrap):
    def __init__(self, charm_class, controller, actions=None,
                 show_constraints=False):
        self.charm_class = charm_class
        self.controller = controller
        if actions is None:
            self.actions = []
        else:
            self.actions = actions
        self.show_constraints = show_constraints
        w = self.build_widgets()
        self.update()
        super().__init__(w)

    def selectable(self):
        return True

    def build_widgets(self):
        self.charm_info_widget = Text("\N{GEAR} {}".format(
            self.charm_class.display_name))
        self.assignments_widget = Text("")

        if self.charm_class.constraints is None:
            c_str = "no constraints set"
        else:
            cpairs = ["{}={}".format(k, v) for k, v in
                      self.charm_class.constraints.items()]
            c_str = 'constraints: ' + ', '.join(cpairs)
        self.constraints_widget = Text(c_str)

        buttons = []
        for label, func in self.actions:
            b = Button(label, on_press=func, user_data=self.charm_class)
            buttons.append(b)

        button_grid = GridFlow(buttons, BUTTON_SIZE, 1, 1, 'right')

        pl = [self.charm_info_widget, self.assignments_widget]
        if self.show_constraints:
            pl.append(self.constraints_widget)
        pl.append(button_grid)

        p = Pile(pl)
        return Padding(p, left=2, right=2)

    def update(self):
        ml = self.controller.machines_for_charm(self.charm_class)

        t = "  "
        if len(ml) == 0:
            t += "\N{DOTTED CIRCLE}"
        else:
            t += ", ".join(["\N{TAPE DRIVE} {}".format(m.hostname)
                            for m in ml])
        self.assignments_widget.set_text(t)


class MachinesList(WidgetWrap):
    """A list of machines with configurable action buttons for each
    machine.

    actions - a list of ('label', function) pairs that wil be used to
    create buttons for each machine.  The machine will be passed to
    the function as userdata.

    constraints - a dict of constraints to filter the machines list.
    only machines matching all the constraints will be shown.
    """

    def __init__(self, controller, actions, constraints=None):
        self.controller = controller
        self.actions = actions
        self.machine_widgets = []
        if constraints is None:
            self.constraints = {}
        else:
            self.constraints = constraints
        w = self.build_widgets()
        super().__init__(w)

    def selectable(self):
        # overridden to ensure that we can arrow through the buttons
        # shouldn't be necessary according to documented behavior of
        # Pile & Columns, but discovered via trial & error.
        return True

    def build_widgets(self):
        if len(self.constraints) > 0:
            cstr = " matching constraints"
        else:
            cstr = ""
        self.machine_pile = Pile([Text("Machines" + cstr)] +
                                 self.machine_widgets)
        return self.machine_pile

    def update(self):

        def find_widget(m):
            return next((mw for mw in self.machine_widgets if
                         mw.machine.instance_id == m.instance_id), None)

        for m in [m for m in self.controller.machines()
                  if m.matches(self.constraints)]:
            mw = find_widget(m)
            if mw is None:
                mw = self.add_machine_widget(m)
            mw.update()

    def add_machine_widget(self, machine):
        mw = MachineWidget(machine, self.controller, self.actions)
        self.machine_widgets.append(mw)
        options = self.machine_pile.options()
        self.machine_pile.contents.append((mw, options))
        return mw


class ServicesList(WidgetWrap):
    """A list of services (charm classes) with configurable action buttons
    for each machine.

    actions - a list of ('label', function) pairs that wil be used to
    create buttons for each machine.  The machine will be passed to
    the function as userdata.
    """

    def __init__(self, controller, actions):
        self.controller = controller
        self.actions = actions
        self.service_widgets = []
        w = self.build_widgets()
        super().__init__(w)

    def selectable(self):
        # overridden to ensure that we can arrow through the buttons
        # shouldn't be necessary according to documented behavior of
        # Pile & Columns, but discovered via trial & error.
        return True

    def build_widgets(self):
        self.service_pile = Pile([Text("Services")] +
                                 self.service_widgets)
        return self.service_pile

    def update(self):

        def find_widget(cc):
            return next((sw for sw in self.service_widgets if
                         sw.charm_class.charm_name == cc.charm_name), None)

        for cc in self.controller.charm_classes():
            sw = find_widget(cc)
            if sw is None:
                sw = self.add_service_widget(cc)
            sw.update()

    def add_service_widget(self, charm_class):
        sw = ServiceWidget(charm_class, self.controller, self.actions)
        self.service_widgets.append(sw)
        options = self.service_pile.options()
        self.service_pile.contents.append((sw, options))
        return sw


class MachineChooser(WidgetWrap):
    """Presents list of machines to assign a service to.
    Supports multiple selection if the service does.
    """

    def __init__(self, controller, charm_class, parent_widget):
        self.controller = controller
        self.charm_class = charm_class
        self.parent_widget = parent_widget
        w = self.build_widgets()
        super().__init__(w)

    def build_widgets(self):

        if self.charm_class.allow_multi_units:
            machine_string = "machines"
            plural_string = "s"
        else:
            machine_string = "a machine"
            plural_string = ""
        instructions = Text("Select {} to host {}".format(
            machine_string, self.charm_class.display_name))

        self.service_widget = ServiceWidget(self.charm_class,
                                            self.controller,
                                            show_constraints=True)

        constraints = self.charm_class.constraints
        self.machines_list = MachinesList(self.controller,
                                          [('Select', self.do_select)],
                                          constraints=constraints)
        self.machines_list.update()
        p = Pile([instructions, Divider(), self.service_widget,
                  Divider('-'), self.machines_list,
                  GridFlow([Button('Close',
                                   on_press=self.close_pressed)],
                           BUTTON_SIZE, 1, 1, 'right')])

        return LineBox(p, title="Select Machine{}".format(plural_string))

    def do_select(self, sender, machine):
        self.controller.assign(machine.instance_id, self.charm_class)
        self.machines_list.update()
        self.service_widget.update()

    def close_pressed(self, sender):
        self.parent_widget.remove_overlay(self)


class ServiceChooser(WidgetWrap):
    """Presents list of services to put on a machine.

    Supports multiple selection, implying separate containers using
    --to.

    """

    def __init__(self, controller, machine, parent_widget):
        self.controller = controller
        self.machine = machine
        self.parent_widget = parent_widget
        w = self.build_widgets()
        super().__init__(w)

    def build_widgets(self):

        instructions = Text("Select services to add to {}".format(
            self.machine.hostname))

        self.machine_widget = MachineWidget(self.machine,
                                            self.controller,
                                            show_hardware=True)
        self.services_list = ServicesList(self.controller,
                                          [('Select', self.do_select)])
        self.services_list.update()
        p = Pile([instructions, Divider(), self.machine_widget,
                  Divider('-'), self.services_list,
                  GridFlow([Button('Close',
                                   on_press=self.close_pressed)],
                           BUTTON_SIZE, 1, 1, 'right')])

        return LineBox(p, title="Select Services")

    def do_select(self, sender, charm_class):
        self.controller.assign(self.machine.instance_id, charm_class)
        self.services_list.update()

    def close_pressed(self, sender):
        self.parent_widget.remove_overlay(self)


class PlacementView(WidgetWrap):
    """Handles display of machines and services.

    displays nothing if self.controller is not set.
    set it to a PlacementController.
    """

    def __init__(self, controller):
        self.controller = controller
        w = self.build_widgets()
        super().__init__(w)
        self.update()

    def update(self):
        self.machines_list.update()
        self.services_list.update()

    def scroll_down(self):
        pass

    def scroll_up(self):
        pass

    def build_widgets(self):
        self.charm_store_pile = Pile([Text("Add Charms")])

        self.machines_list = MachinesList(self.controller,
                                          [('Clear', self.do_clear_machine),
                                           ('Pick Services',
                                            self.do_show_service_chooser)])
        self.machines_list.update()

        self.services_list = ServicesList(self.controller,
                                          [('Clear', self.do_clear_service),
                                           ('Pick Machine(s)',
                                            self.do_show_machine_chooser)])
        self.services_list.update()

        cols = Columns([self.charm_store_pile,
                        self.services_list,
                        self.machines_list])

        return Filler(cols, valign='top')

    def do_clear_machine(self, sender, machine):
        self.controller.clear_assignments(machine)

    def do_clear_service(self, sender, charm_class):
        for m in self.controller.machines_for_charm(charm_class):
            self.controller.remove_assignment(m, charm_class)

    def do_show_service_chooser(self, sender, machine):
        self.show_overlay(Filler(ServiceChooser(self.controller,
                                                machine,
                                                self)))

    def do_show_machine_chooser(self, sender, charm_class):
        self.show_overlay(Filler(MachineChooser(self.controller,
                                                charm_class,
                                                self)))

    def show_overlay(self, overlay_widget):
        self.orig_w = self._w
        self._w = Overlay(top_w=overlay_widget,
                          bottom_w=self._w,
                          align='center',
                          width=('relative', 60),
                          min_width=80,
                          valign='middle',
                          height=('relative', 80))

    def remove_overlay(self, overlay_widget):
        # urwid note: we could also get orig_w as
        # self._w.contents[0][0], but this is clearer:
        self._w = self.orig_w
