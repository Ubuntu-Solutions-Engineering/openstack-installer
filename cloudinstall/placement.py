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

from urwid import (AttrMap, Button, Columns, Divider, Filler, GridFlow,
                   LineBox, Overlay, Padding, Pile, Text, WidgetWrap)

from cloudinstall.machine import satisfies
from cloudinstall.ui import InfoDialog
from cloudinstall.utils import load_charms, format_constraint

log = logging.getLogger('cloudinstall.placement')


BUTTON_SIZE = 20


class PlaceholderMachine:
    """A dummy machine that doesn't map to an existing maas machine"""

    is_placeholder = True

    def __init__(self, instance_id, name):
        self.instance_id = instance_id
        self.system_id = instance_id
        self.display_name = name
        self.constraints = defaultdict(lambda: '*')

    @property
    def machine(self):
        return self.constraints

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

    def __repr__(self):
        return "<Placeholder Machine: {}>".format(self.display_name)


class PlacementController:
    """Keeps state of current machines and their assigned services.
    """

    def __init__(self, maas_state, opts):
        self.maas_state = maas_state
        self.assignments = defaultdict(list)  # instance_id -> [charm class]
        self.opts = opts
        self.unplaced_services = set()

    def machines(self):
        return self.maas_state.machines()

    def charm_classes(self):
        cl = [m.__charm_class__ for m in load_charms()
              if not m.__charm_class__.optional and
              not m.__charm_class__.disabled]

        if self.opts.enable_swift:
            for m in load_charms():
                n = m.__charm_class__.name()
                if n == "swift-storage" or n == "swift-proxy":
                    cl.append(m.__charm_class__)
        return cl

    def assign(self, instance_id, charm_class):
        if not charm_class.allow_multi_units:
            for m, l in self.assignments.items():
                if charm_class in l:
                    l.remove(charm_class)
        self.assignments[instance_id].append(charm_class)
        self.reset_unplaced()

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
        self.reset_unplaced()

    def clear_assignments(self, m):
        del self.assignments[m.instance_id]
        self.reset_unplaced()

    def assignments_for_machine(self, m):
        return self.assignments[m.instance_id]

    def set_all_assignments(self, assignments):
        self.assignments = assignments
        self.reset_unplaced()

    def reset_unplaced(self):
        self.unplaced_services = set()
        for cc in self.charm_classes():
            ms = self.machines_for_charm(cc)
            if len(ms) == 0:
                self.unplaced_services.add(cc)

    def can_deploy(self):
        uncore_services = ['swift-storage',
                           'swift-proxy',
                           'nova-compute']
        core_services = set([cc.__charm_class__ for cc in load_charms()
                             if cc.__charm_class__.name() not in
                             uncore_services])
        unplaced_cores = core_services.intersection(
            self.unplaced_services)

        return len(unplaced_cores) == 0

    def autoplace_unplaced_services(self):
        """Attempt to find machines for all unplaced services using only empty
        machines.

        Returns a pair (success, message) where success is True if all
        services are placed. message is an info message for the user.
        """

        empty_machines = [m for m in self.machines()
                          if len(self.assignments[m.instance_id]) == 0]

        unplaced_defaults = self.gen_defaults(list(self.unplaced_services),
                                              empty_machines)

        for mid, charm_classes in unplaced_defaults.items():
            self.assignments[mid] = charm_classes

        self.reset_unplaced()

        if len(self.unplaced_services) > 0:
            msg = ("Not enough empty machines could be found for the required"
                   " services. Please add machines or finish placement "
                   "manually.")
            return (False, msg)
        return (True, "")

    def gen_defaults(self, charm_classes=None, maas_machines=None):
        """Generates an assignments dictionary for the given charm classes and
        machines, based on constraints.

        Does not alter controller state.

        Use set_all_assignments(gen_defaults()) to clear and reset the
        controller's state to these defaults.

        """
        if charm_classes is None:
            charm_classes = self.charm_classes()

        assignments = defaultdict(list)

        if maas_machines is None:
            maas_machines = self.maas_state.machines()

        def satisfying_machine(constraints):
            for machine in maas_machines:
                if satisfies(machine, constraints)[0]:
                    maas_machines.remove(machine)
                    return machine

            return None

        isolated_charms, controller_charms = [], []

        for charm_class in charm_classes:
            if charm_class.isolate:
                isolated_charms.append(charm_class)
            else:
                controller_charms.append(charm_class)

        for charm_class in isolated_charms:
            m = satisfying_machine(charm_class.constraints)
            if m:
                assignments[m.instance_id].append(charm_class)

        controller_machine = satisfying_machine({})
        if controller_machine:
            for charm_class in controller_charms:
                assignments[controller_machine.instance_id].append(charm_class)

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
        if self.machine.instance_id == 'unplaced':
            self.machine_info_widget = Text(('info',
                                             "\N{DOTTED CIRCLE} Unplaced"))
        else:
            self.machine_info_widget = Text("\N{TAPE DRIVE} {}".format(
                self.machine.hostname))
        self.assignments_widget = Text("")

        self.hardware_widget = Text(["  "] + self.hardware_info_markup())

        buttons = []
        for label, func in self.actions:
            if label == 'Clear' and self.machine.instance_id == 'unplaced':
                continue
            b = AttrMap(Button(label, on_press=func, user_data=self.machine),
                        'button')
            buttons.append(b)

        button_grid = GridFlow(buttons, BUTTON_SIZE, 1, 1, 'right')

        pl = [Divider(' '), self.machine_info_widget, self.assignments_widget]
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
                 show_constraints=False,
                 show_assignments=False):
        self.charm_class = charm_class
        self.controller = controller
        if actions is None:
            self.actions = []
        else:
            self.actions = actions
        self.show_constraints = show_constraints
        self.show_assignments = show_assignments
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
            c_str = "  no constraints set"
        else:
            cpairs = [format_constraint(k, v) for k, v in
                      self.charm_class.constraints.items()]
            c_str = "  constraints: " + ', '.join(cpairs)
        self.constraints_widget = Text(c_str)

        buttons = []
        for label, func in self.actions:
            b = AttrMap(Button(label, on_press=func,
                               user_data=self.charm_class),
                        'button')
            buttons.append(b)

        button_grid = GridFlow(buttons, BUTTON_SIZE, 1, 1, 'right')

        pl = [self.charm_info_widget]
        if self.show_assignments:
            pl.append(self.assignments_widget)
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

    show_hardware - bool, whether or not to show the hardware details
    for each of the machines

    """

    def __init__(self, controller, actions, constraints=None,
                 show_hardware=False):
        self.controller = controller
        self.actions = actions
        self.machine_widgets = []
        if constraints is None:
            self.constraints = {}
        else:
            self.constraints = constraints
        self.show_hardware = show_hardware
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

        for m in self.controller.machines():
            if not satisfies(m, self.constraints)[0]:
                continue
            mw = find_widget(m)
            if mw is None:
                mw = self.add_machine_widget(m)
            mw.update()

    def add_machine_widget(self, machine):
        mw = MachineWidget(machine, self.controller, self.actions,
                           self.show_hardware)
        self.machine_widgets.append(mw)
        options = self.machine_pile.options()
        self.machine_pile.contents.append((mw, options))

        self.machine_pile.contents.append((AttrMap(Padding(Divider('\u23bc'),
                                                           left=2, right=2),
                                                   'label'), options))
        return mw


class ServicesList(WidgetWrap):
    """A list of services (charm classes) with configurable action buttons
    for each machine.

    actions - a list of ('label', function) pairs that wil be used to
    create buttons for each machine.  The machine will be passed to
    the function as userdata.

    machine - a machine instance to query for constraint checking

    show_constraints - bool, whether or not to show the constraints
    for the various services

    """

    def __init__(self, controller, actions, machine=None,
                 unplaced_only=False, show_constraints=False):
        self.controller = controller
        self.actions = actions
        self.service_widgets = []
        self.machine = machine
        self.unplaced_only = unplaced_only
        self.show_constraints = show_constraints
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

    def find_service_widget(self, cc):
        return next((sw for sw in self.service_widgets if
                     sw.charm_class.charm_name == cc.charm_name), None)

    def update(self):
        for cc in self.controller.charm_classes():
            if self.machine and not satisfies(self.machine,
                                              cc.constraints)[0]:
                self.remove_service_widget(cc)
                continue

            if self.unplaced_only and \
               cc not in self.controller.unplaced_services:
                self.remove_service_widget(cc)
                continue

            sw = self.find_service_widget(cc)
            if sw is None:
                sw = self.add_service_widget(cc)
            sw.update()

    def add_service_widget(self, charm_class):
        sw = ServiceWidget(charm_class, self.controller, self.actions,
                           self.show_constraints)
        self.service_widgets.append(sw)
        options = self.service_pile.options()
        self.service_pile.contents.append((sw, options))
        self.service_pile.contents.append((AttrMap(Padding(Divider('\u23bc'),
                                                           left=2, right=2),
                                                   'label'), options))
        return sw

    def remove_service_widget(self, charm_class):
        sw = self.find_service_widget(charm_class)

        if sw is None:
            return
        self.service_widgets.remove(sw)
        sw_idx = 0
        for w, opts in self.service_pile.contents:
            if w == sw:
                break
            sw_idx += 1

        c = self.service_pile.contents[:sw_idx] + \
            self.service_pile.contents[sw_idx + 2:]
        self.service_pile.contents = c


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
                                          constraints=constraints,
                                          show_hardware=True)
        self.machines_list.update()
        p = Pile([instructions, Divider(), self.service_widget,
                  Divider(), self.machines_list,
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
                                          [('Select', self.do_select)],
                                          machine=self.machine,
                                          show_constraints=True)
        self.services_list.update()
        p = Pile([instructions, Divider(), self.machine_widget,
                  Divider(), self.services_list,
                  GridFlow([Button('Close',
                                   on_press=self.close_pressed)],
                           BUTTON_SIZE, 1, 1, 'right')])

        return LineBox(p, title="Select Services")

    def do_select(self, sender, charm_class):
        self.controller.assign(self.machine.instance_id, charm_class)
        self.services_list.update()

    def close_pressed(self, sender):
        self.parent_widget.remove_overlay(self)


class ControlColumn(WidgetWrap):
    """Handles display of the left-hand column with dynamic buttons and
    list of unplaced services.
    """
    def __init__(self, display_controller, placement_controller,
                 placement_view):
        self.display_controller = display_controller
        self.placement_controller = placement_controller
        self.placement_view = placement_view
        w = self.build_widgets()
        super().__init__(w)
        self.update()

    def selectable(self):
        return True

    def build_widgets(self):
        actions = [("Choose Machine",
                    self.placement_view.do_show_machine_chooser)]
        self.unplaced_services_list = ServicesList(self.placement_controller,
                                                   actions,
                                                   unplaced_only=True,
                                                   show_constraints=True)
        self.autoplace_button = Button(('button',
                                        "Auto-place remaining services"),
                                       on_press=self.do_autoplace)
        self.reset_button = Button(('button',
                                    "Reset to default placement"),
                                   on_press=self.do_reset_to_defaults)

        self.deploy_button = Button(('deploybutton', "Deploy"),
                                    on_press=self.do_commit_and_deploy)

        deploy_ok_msg = Text([('success_icon', '\u2713'),
                              " All the core OpenStack services are placed"
                              " on a machine, and you can now deploy."])
        self.deploy_widgets = Pile([deploy_ok_msg, self.deploy_button])

        self.unplaced_services_pile = Pile([self.unplaced_services_list,
                                            self.autoplace_button,
                                            Divider()])

        unplaced_msg = Text("The following core services must be placed "
                            "before deploying:")

        self.unplaced_warning_widgets = Pile([Text(('info', "NOTE")),
                                              unplaced_msg])
        pl = [Padding(Text("Machine Placement"), align='center',
                      width=('relative', 100)),
              Pile([]),         # placeholders replaced in update()
              Pile([]),
              Pile([])]

        self.main_pile = Pile(pl)

        return self.main_pile

    def update(self):

        self.unplaced_services_list.update()
        if self.placement_controller.can_deploy():
            self.main_pile.contents[1] = (self.deploy_widgets,
                                          self.main_pile.options())
        else:
            self.main_pile.contents[1] = (self.unplaced_warning_widgets,
                                          self.main_pile.options())

        if len(self.placement_controller.unplaced_services) == 0:
            self.main_pile.contents[2] = (Divider(),
                                          self.main_pile.options())
        else:
            self.main_pile.contents[2] = (self.unplaced_services_pile,
                                          self.main_pile.options())

        defs = self.placement_controller.gen_defaults()
        if self.placement_controller.assignments == defs:
            self.main_pile.contents[3] = (Divider(),
                                          self.main_pile.options())
        else:
            self.main_pile.contents[3] = (self.reset_button,
                                          self.main_pile.options())

    def do_reset_to_defaults(self, sender):
        self.placement_controller.set_all_assignments(
            self.placement_controller.gen_defaults())

    def do_autoplace(self, sender):
        ok, msg = self.placement_controller.autoplace_unplaced_services()
        if not ok:
            self.show_overlay(Filler(InfoDialog(msg,
                                                self.remove_overlay)))

    def do_commit_and_deploy(self, sender):
        self.display_controller.commit_placement()


class PlacementView(WidgetWrap):
    """Handles display of machines and services.

    displays nothing if self.controller is not set.
    set it to a PlacementController.
    """

    def __init__(self, display_controller, placement_controller):
        self.display_controller = display_controller
        self.placement_controller = placement_controller
        w = self.build_widgets()
        super().__init__(w)
        self.update()

    def scroll_down(self):
        pass

    def scroll_up(self):
        pass

    def build_widgets(self):
        self.control_column = ControlColumn(self.display_controller,
                                            self.placement_controller,
                                            self)

        self.machines_list = MachinesList(self.placement_controller,
                                          [('Clear', self.do_clear_machine),
                                           ('Edit Services',
                                            self.do_show_service_chooser)],
                                          show_hardware=True)
        self.machines_list.update()

        self.machine_detail_view = Pile([Text("TODO")])

        self.columns = Columns([self.control_column,
                                self.machines_list,
                                self.machine_detail_view])

        return Filler(self.columns, valign='top')

    def update(self):
        self.control_column.update()
        self.machines_list.update()

    def do_clear_machine(self, sender, machine):
        self.placement_controller.clear_assignments(machine)

    def do_clear_service(self, sender, charm_class):
        for m in self.placement_controller.machines_for_charm(charm_class):
            self.placement_controller.remove_assignment(m, charm_class)

    def do_show_service_chooser(self, sender, machine):
        self.show_overlay(Filler(ServiceChooser(self.placement_controller,
                                                machine,
                                                self)))

    def do_show_machine_chooser(self, sender, charm_class):
        self.show_overlay(Filler(MachineChooser(self.placement_controller,
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
