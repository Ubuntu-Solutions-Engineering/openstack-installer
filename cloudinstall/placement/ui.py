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
from subprocess import Popen, PIPE, TimeoutExpired

from urwid import (AttrMap, Button, Columns, connect_signal, Divider,
                   Edit, Filler, GridFlow, LineBox, Overlay, Padding,
                   Pile, SelectableIcon, Text, WidgetWrap)

from cloudinstall.config import Config
from cloudinstall.machine import satisfies
from cloudinstall.placement.controller import AssignmentType
from cloudinstall.ui import InfoDialog
from cloudinstall.utils import format_constraint

log = logging.getLogger('cloudinstall.placement')


BUTTON_SIZE = 20


class FilterBox(WidgetWrap):

    def __init__(self, edit_changed_cb):
        self.label = Text("")
        self.info_text = Text("")
        self.editbox = Edit()
        connect_signal(self.editbox, 'change',
                       edit_changed_cb)

        w = Pile([Columns([('pack', self.label),
                           AttrMap(self.editbox,
                                   'filter', 'filter_focus')])
                  self.info_text # -- WORKAROUND for issue #194
                  ])
        super().__init__(w)

    def set_info(self, n_showing, n_total):
        m = ["Filter ", ('label', "({} of {} shown): ".format(n_showing,
                                                              n_total))]
        self.label.set_text(m)
        if False:   # WORKAROUND for issue #194
            t = ''
        else:
            t = ('label',
                 "  Filter on hostname or hardware info like 'cores:4'")
        self.info_text.set_text(t)


class MachineWidget(WidgetWrap):

    """A widget displaying a service and associated actions.

    machine - the machine to display

    controller - a PlacementController instance

    actions - a list of ('label', function) pairs that wil be used to
    create buttons for each machine.  The machine will be passed to
    the function as userdata.

    optionally, actions can be a 3-tuple (pred, 'label', function),
    where pred determines whether to add the button. Pred will be
    passed the charm class.

    show_hardware - display hardware details about this machine

    show_assignments - display info about which charms are assigned
    and what assignment type (LXC, KVM, etc) they have.
    """

    def __init__(self, machine, controller, actions=None,
                 show_hardware=False, show_assignments=True):
        self.machine = machine
        self.controller = controller
        if actions is None:
            self.actions = []
        else:
            self.actions = actions
        self.show_hardware = show_hardware
        self.show_assignments = show_assignments
        w = self.build_widgets()
        self.update()
        super().__init__(w)

    def selectable(self):
        return True

    def hardware_info_markup(self):
        m = self.machine
        return [('label', 'arch'), ' {}  '.format(m.arch),
                ('label', 'cores'), ' {}  '.format(m.cpu_cores),
                ('label', 'mem'), ' {}  '.format(m.mem),
                ('label', 'storage'), ' {}'.format(m.storage)]

    def build_widgets(self):

        self.machine_info_widget = Text("")
        self.assignments_widget = Text("")
        self.hardware_widget = Text("")

        self.buttons = []
        self.button_grid = GridFlow(self.buttons, 22, 1, 1, 'right')

        pl = [Divider(' '), self.machine_info_widget]
        if self.show_hardware:
            pl.append(self.hardware_widget)
        if self.show_assignments:
            pl += [Divider(' '), self.assignments_widget]
        pl.append(self.button_grid)

        p = Pile(pl)

        return Padding(p, left=2, right=2)

    def update_machine(self):
        """Refresh with potentially updated machine info from controller.
        Assumes that machine exists - machines going away is handled
        in machineslist.update().
        """
        self.machine = next((m for m in self.controller.machines()
                             if m.instance_id == self.machine.instance_id),
                            None)

    def update(self):
        self.update_machine()
        info_markup = ["\N{TAPE DRIVE} {}".format(self.machine.hostname),
                       ('label', " ({})".format(self.machine.status))]

        self.machine_info_widget.set_text(info_markup)
        self.hardware_widget.set_text(["  "] + self.hardware_info_markup())

        ad = self.controller.assignments_for_machine(self.machine)
        astr = [('label', "  Services: ")]

        for atype, al in ad.items():
            n = len(al)
            if n == 1:
                pl_s = ""
            else:
                pl_s = "s"
            if atype == AssignmentType.BareMetal:
                astr.append(('label', "\n    {} service{}"
                             " on Bare Metal: ".format(n, pl_s)))
            else:
                astr.append(('label', "\n    {} "
                             "{}{}: ".format(n, atype.name, pl_s)))
            if n == 0:
                astr.append("\N{EMPTY SET}")
            else:
                astr.append(", ".join(["\N{GEAR} {}".format(c.display_name)
                                       for c in al]))

        self.assignments_widget.set_text(astr)
        self.update_buttons()

    def update_buttons(self):
        buttons = []
        for at in self.actions:
            if len(at) == 2:
                predicate = lambda x: True
                label, func = at
            else:
                predicate, label, func = at

            if not predicate(self.machine):
                b = AttrMap(SelectableIcon(" (" + label + ")"),
                            'disabled_button', 'disabled_button_focus')
            else:
                b = AttrMap(Button(label, on_press=func,
                                   user_data=self.machine),
                            'button', 'button_focus')
            buttons.append((b, self.button_grid.options()))

        self.button_grid.contents = buttons


class ServiceWidget(WidgetWrap):

    """A widget displaying a service and associated actions.

    charm_class - the class describing the service to display

    controller - a PlacementController instance

    actions - a list of ('label', function) pairs that wil be used to
    create buttons for each machine.  The machine will be passed to
    the function as userdata.

    optionally, actions can be a 3-tuple (pred, 'label', function),
    where pred determines whether to add the button. Pred will be
    passed the charm class.

    show_constraints - display the charm's constraints

    show_assignments - display the machine(s) currently assigned to
    host this service

    """

    def __init__(self, charm_class, controller, actions=None,
                 show_constraints=False, show_assignments=False,
                 show_required_label=False):
        self.charm_class = charm_class
        self.controller = controller
        if actions is None:
            self.actions = []
        else:
            self.actions = actions
        self.show_constraints = show_constraints
        self.show_assignments = show_assignments
        self.show_required_label = show_required_label
        w = self.build_widgets()
        self.update()
        super().__init__(w)

    def selectable(self):
        return True

    def build_widgets(self):
        dn = self.charm_class.display_name
        self.title_markup = ["\N{GEAR} {}".format(dn), ""]

        self.charm_info_widget = Text(self.title_markup)
        self.assignments_widget = Text("")

        if len(self.charm_class.constraints) == 0:
            c_str = [('label', "  no constraints set")]
        else:
            cpairs = [format_constraint(k, v) for k, v in
                      self.charm_class.constraints.items()]
            c_str = [('label', "  constraints: "), ', '.join(cpairs)]
        self.constraints_widget = Text(c_str)

        self.buttons = []

        self.button_grid = GridFlow(self.buttons, 22, 1, 1, 'right')

        pl = [self.charm_info_widget]
        if self.show_assignments:
            pl.append(self.assignments_widget)
        if self.show_constraints:
            pl.append(self.constraints_widget)
        pl.append(self.button_grid)

        p = Pile(pl)
        return Padding(p, left=2, right=2)

    def update(self):
        md = self.controller.machines_for_charm(self.charm_class)
        mstr = [""]

        if self.controller.service_is_core(self.charm_class):
            np = self.controller.machine_count_for_charm(self.charm_class)
            nr = self.charm_class.required_num_units()
            self.title_markup[1] = ('info',
                                    " ({} of {} placed)".format(np, nr))
            self.charm_info_widget.set_text(self.title_markup)

        for atype, ml in md.items():
            n = len(ml)
            mstr.append(('label', "    {} ({}): ".format(atype.name, n)))
            if len(ml) == 0:
                mstr.append("\N{DOTTED CIRCLE}")
            else:
                mstr.append(", ".join(["\N{TAPE DRIVE} {}".format(m.hostname)
                                       for m in ml]))
            mstr.append("\n")
        self.assignments_widget.set_text(mstr)

        self.update_buttons()

    def update_buttons(self):
        buttons = []
        for at in self.actions:
            if len(at) == 2:
                predicate = lambda x: True
                label, func = at
            else:
                predicate, label, func = at

            if not predicate(self.charm_class):
                b = AttrMap(SelectableIcon(" (" + label + ")"),
                            'disabled_button', 'disabled_button_focus')
            else:
                b = AttrMap(Button(label, on_press=func,
                                   user_data=self.charm_class),
                            'button', 'button_focus')
            buttons.append((b, self.button_grid.options()))

        self.button_grid.contents = buttons


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

        for m in machines:
            if not satisfies(m, self.constraints)[0]:
                self.remove_machine(m)
                continue

            if self.filter_string != "" and \
               self.filter_string not in m.filter_label():
                self.remove_machine(m)
                continue

            mw = self.find_machine_widget(m)
            if mw is None:
                mw = self.add_machine_widget(m)
            mw.update()

        self.filter_edit_box.set_info(len(self.machine_widgets),
                                      len(machines))

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


class ServicesList(WidgetWrap):

    """A list of services (charm classes) with configurable action buttons
    for each machine.

    actions - a list of tuples describing buttons. Passed to
    ServiceWidget.

    machine - a machine instance to query for constraint checking

    show_constraints - bool, whether or not to show the constraints
    for the various services

    """

    def __init__(self, controller, actions, machine=None,
                 unplaced_only=False, show_type='all',
                 show_constraints=False,
                 title="Services"):
        self.controller = controller
        self.actions = actions
        self.service_widgets = []
        self.machine = machine
        self.unplaced_only = unplaced_only
        self.show_type = show_type
        self.show_constraints = show_constraints
        self.title = title
        w = self.build_widgets()
        self.update()
        super().__init__(w)

    def selectable(self):
        # overridden to ensure that we can arrow through the buttons
        # shouldn't be necessary according to documented behavior of
        # Pile & Columns, but discovered via trial & error.
        return True

    def build_widgets(self):
        self.service_pile = Pile([Text(self.title),
                                  Divider(' ')] +
                                 self.service_widgets)
        return self.service_pile

    def find_service_widget(self, cc):
        return next((sw for sw in self.service_widgets if
                     sw.charm_class.charm_name == cc.charm_name), None)

    def update(self):

        for cc in self.controller.charm_classes():
            if self.machine:
                if not satisfies(self.machine, cc.constraints)[0] \
                   or not self.controller.is_assigned(cc, self.machine):
                    self.remove_service_widget(cc)
                    continue

            if self.unplaced_only:
                n_units = self.controller.machine_count_for_charm(cc)
                if n_units == cc.required_num_units() \
                   and cc not in self.controller.unplaced_services:
                    self.remove_service_widget(cc)
                    continue

            is_core = self.controller.service_is_core(cc)
            if self.show_type == 'core':
                if not is_core:
                    continue
            elif self.show_type == 'non-core':
                if is_core:
                    self.remove_service_widget(cc)
                    continue
                if not cc.allow_multi_units and \
                        cc not in self.controller.unplaced_services:
                    self.remove_service_widget(cc)
                    continue

            sw = self.find_service_widget(cc)
            if sw is None:
                sw = self.add_service_widget(cc)
            sw.update()

    def add_service_widget(self, charm_class):
        sw = ServiceWidget(charm_class, self.controller, self.actions,
                           self.show_constraints,
                           show_required_label=self.unplaced_only)
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
                                            show_constraints=True,
                                            show_assignments=True)

        all_actions = [(AssignmentType.BareMetal,
                        'Add as Bare Metal',
                        self.do_select_baremetal),
                       (AssignmentType.LXC,
                        'Add as LXC', self.do_select_lxc),
                       (AssignmentType.KVM,
                        'Add as KVM', self.do_select_kvm)]

        actions = [(label, func) for atype, label, func in all_actions
                   if atype in self.charm_class.allowed_assignment_types]

        constraints = self.charm_class.constraints
        # NOTE: show_assignments=False is a WORKAROUND for #194
        self.machines_list = MachinesList(self.controller,
                                          actions,
                                          constraints=constraints,
                                          show_hardware=True,
                                          show_assignments=False)
        self.machines_list.update()
        close_button = AttrMap(Button('X',
                                      on_press=self.close_pressed),
                               'button', 'button_focus')
        p = Pile([GridFlow([close_button], 5, 1, 0, 'right'),
                  instructions, Divider(), self.service_widget,
                  Divider(), self.machines_list])

        return LineBox(p, title="Select Machine{}".format(plural_string))

    def do_select_baremetal(self, sender, machine):
        self.do_select(sender, machine, AssignmentType.BareMetal)

    def do_select_lxc(self, sender, machine):
        self.do_select(sender, machine, AssignmentType.LXC)

    def do_select_kvm(self, sender, machine):
        self.do_select(sender, machine, AssignmentType.KVM)

    def do_select(self, sender, machine, atype):
        self.controller.assign(machine, self.charm_class, atype)
        self.machines_list.update()
        self.service_widget.update()
        self.parent_widget.remove_overlay(self)

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

        instructions = Text("Remove services from {}".format(
            self.machine.hostname))

        self.machine_widget = MachineWidget(self.machine,
                                            self.controller,
                                            show_hardware=True)

        def show_remove_p(cc):
            md = self.controller.machines_for_charm(cc)
            for atype, ms in md.items():
                hostnames = [m.hostname for m in ms]
                if self.machine.hostname in hostnames:
                    return True
            return False

        self.services_list = ServicesList(self.controller,
                                          [(show_remove_p, 'Remove',
                                            self.do_remove)],
                                          machine=self.machine)

        close_button = AttrMap(Button('X',
                                      on_press=self.close_pressed),
                               'button', 'button_focus')
        p = Pile([GridFlow([close_button], 5, 1, 0, 'right'),
                  instructions, Divider(), self.machine_widget,
                  Divider(), self.services_list])

        return LineBox(p, title="Remove Services")

    def update(self):
        self.machine_widget.update()
        self.services_list.update()

    def do_add(self, sender, charm_class, atype):
        self.controller.assign(self.machine, charm_class, atype)
        self.update()

    def do_remove(self, sender, charm_class):
        self.controller.remove_one_assignment(self.machine,
                                              charm_class)
        self.update()

    def close_pressed(self, sender):
        self.parent_widget.remove_overlay(self)


class ServicesColumn(WidgetWrap):

    """Displays dynamic list of unplaced services and associated controls
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
        self.deploy_view = DeployView(self.display_controller,
                                      self.placement_controller,
                                      self.placement_view)

        actions = [("Choose Machine",
                    self.placement_view.do_show_machine_chooser)]
        self.required_services_list = ServicesList(self.placement_controller,
                                                   actions,
                                                   unplaced_only=True,
                                                   show_type='core',
                                                   show_constraints=True,
                                                   title="Required Services")
        self.additional_services_list = ServicesList(self.placement_controller,
                                                     actions,
                                                     show_type='non-core',
                                                     show_constraints=True,
                                                     title="Additional "
                                                     "Services")

        autoplace_func = self.placement_view.do_autoplace
        self.autoplace_button = AttrMap(Button("Auto-place Remaining Services",
                                               on_press=autoplace_func),
                                        'button', 'button_focus')

        clear_all_func = self.placement_view.do_clear_all
        self.clear_all_button = AttrMap(Button("Clear all Placements",
                                               on_press=clear_all_func),
                                        'button', 'button_focus')

        self.required_services_pile = Pile([self.required_services_list,
                                            Divider()])
        self.additional_services_pile = Pile([self.additional_services_list,
                                              Divider()])

        self.top_buttons = []
        self.top_button_grid = GridFlow(self.top_buttons,
                                        36, 1, 0, 'center')

        pl = [Text(('subheading', "Services"), align='center'),
              Divider(),
              self.top_button_grid, Divider(),
              self.deploy_view, Divider(),
              self.required_services_pile, Divider(),
              self.additional_services_pile]

        self.main_pile = Pile(pl)

        return self.main_pile

    def update(self):
        self.deploy_view.update()
        self.required_services_list.update()
        self.additional_services_list.update()

        top_buttons = []

        if len(self.placement_controller.unplaced_services) == 0:
            icon = SelectableIcon(" (Auto-place Remaining Services) ")
            top_buttons.append((AttrMap(icon,
                                        'disabled_button',
                                        'disabled_button_focus'),
                                self.top_button_grid.options()))

        else:
            top_buttons.append((self.autoplace_button,
                                self.top_button_grid.options()))

        top_buttons.append((self.clear_all_button,
                            self.top_button_grid.options()))

        self.top_button_grid.contents = top_buttons

    def do_reset_to_defaults(self, sender):
        self.placement_controller.set_all_assignments(
            self.placement_controller.gen_defaults())


class DeployView(WidgetWrap):

    def __init__(self, display_controller, placement_controller,
                 placement_view):
        self.display_controller = display_controller
        self.placement_controller = placement_controller
        self.placement_view = placement_view
        self.prev_status = None
        w = self.build_widgets()
        super().__init__(w)
        self.update()

    def selectable(self):
        return True

    def build_widgets(self):
        self.deploy_ok_msg = ("\u2713 All the core OpenStack services are "
                              "placed on a machine, and you can now deploy.")

        self.deploy_button = AttrMap(Button("Deploy",
                                            on_press=self.do_deploy),
                                     'button', 'button_focus')
        self.deploy_grid = GridFlow([self.deploy_button], 10, 1, 0, 'center')

        self.unplaced_msg = "Some core services are still unplaced."

        self.main_pile = Pile([Divider()])
        return self.main_pile

    def update(self):
        changed = self.prev_status != self.placement_controller.can_deploy()

        if self.placement_controller.can_deploy():
            if changed:
                self.show_deploy_button()
        else:
            self.main_pile.contents[0] = (Divider(),
                                          self.main_pile.options())
            if changed:
                self.display_controller.error_message(self.unplaced_msg)

        self.prev_status = self.placement_controller.can_deploy()

    def show_deploy_button(self):
        self.main_pile.contents[0] = (AttrMap(self.deploy_grid,
                                              'deploy_highlight_start'),
                                      self.main_pile.options())

        def fade_timeout(loop, step):
            if step == 1:
                self.display_controller.loop.set_alarm_in(5, fade_timeout, 2)
                new_attr = 'deploy_highlight_end'
            else:
                new_attr = ''
            self.main_pile.contents[0] = (AttrMap(self.deploy_grid,
                                                  new_attr),
                                          self.main_pile.options())

        self.display_controller.loop.set_alarm_in(4, fade_timeout, 1)
        self.display_controller.info_message(self.deploy_ok_msg)

    def do_deploy(self, sender):
        self.display_controller.commit_placement()


class MachinesColumn(WidgetWrap):

    """Shows machines or a link to MAAS to add more"""

    def __init__(self, display_controller, placement_controller,
                 placement_view):
        self.display_controller = display_controller
        self.placement_controller = placement_controller
        self.placement_view = placement_view
        self.config = Config()
        w = self.build_widgets()
        super().__init__(w)
        self.update()

    def selectable(self):
        return True

    def build_widgets(self):

        def has_services_p(m):
            pc = self.placement_controller
            n = sum([len(al) for at, al in
                     pc.assignments_for_machine(m).items()])
            return n > 0

        clear_machine_func = self.placement_view.do_clear_machine
        show_chooser_func = self.placement_view.do_show_service_chooser

        self.open_maas_button = AttrMap(Button("Open in Browser",
                                               on_press=self.browse_maas),
                                        'button', 'button_focus')

        bc = self.config.juju_env['bootstrap-config']
        maasname = "'{}' <{}>".format(bc['name'], bc['maas-server'])
        maastitle = "Connected to MAAS {}".format(maasname)
        tw = Columns([Text(maastitle),
                      Padding(self.open_maas_button, align='right',
                              width=BUTTON_SIZE, right=2)])

        self.machines_list = MachinesList(self.placement_controller,
                                          [(has_services_p,
                                            'Clear All Services',
                                            clear_machine_func),
                                           (has_services_p,
                                            'Remove Some Services',
                                            show_chooser_func)],
                                          show_hardware=True,
                                          title_widgets=tw)
        self.machines_list.update()

        self.machines_list_pile = Pile([self.machines_list,
                                        Divider()])

        # placeholders replaced in update() with absolute indexes, so
        # if you change this list, check update().
        pl = [Text(('subheading', "Machines"), align='center'),
              Divider(),
              Pile([]),         # machines_list
              Divider()]

        self.main_pile = Pile(pl)

        return self.main_pile

    def update(self):
        self.machines_list.update()

        bc = self.config.juju_env['bootstrap-config']
        empty_maas_msg = ("There are no available machines.\n"
                          "Open {} to add machines to "
                          "'{}':".format(bc['maas-server'], bc['name']))

        self.empty_maas_widgets = Pile([Text([('error_icon',
                                               "\N{WARNING SIGN} "),
                                              empty_maas_msg],
                                             align='center'),
                                        Padding(self.open_maas_button,
                                                align='center',
                                                width=BUTTON_SIZE)])

        if len(self.placement_controller.machines()) == 0:
            self.main_pile.contents[2] = (self.empty_maas_widgets,
                                          self.main_pile.options())
        else:
            self.main_pile.contents[2] = (self.machines_list_pile,
                                          self.main_pile.options())

    def browse_maas(self, sender):

        bc = self.config.juju_env['bootstrap-config']
        try:
            p = Popen(["sensible-browser", bc['maas-server']],
                      stdout=PIPE, stderr=PIPE)
            outs, errs = p.communicate(timeout=5)

        except TimeoutExpired:
            # went five seconds without an error, so we assume it's
            # OK. Don't kill it, just let it go:
            return
        e = errs.decode('utf-8')
        msg = "Error opening '{}' in a browser:\n{}".format(bc['name'], e)

        w = InfoDialog(msg, self.placement_view.remove_overlay)
        self.placement_view.show_overlay(w)


class PlacementView(WidgetWrap):

    """Handles display of machines and services.

    displays nothing if self.controller is not set.
    set it to a PlacementController.
    """

    def __init__(self, display_controller, placement_controller):
        self.display_controller = display_controller
        self.placement_controller = placement_controller
        self.config = Config()
        w = self.build_widgets()
        super().__init__(w)
        self.update()

    def scroll_down(self):
        pass

    def scroll_up(self):
        pass

    def build_widgets(self):
        self.services_column = ServicesColumn(self.display_controller,
                                              self.placement_controller,
                                              self)

        self.machines_column = MachinesColumn(self.display_controller,
                                              self.placement_controller,
                                              self)

        self.columns = Columns([self.services_column,
                                self.machines_column])
        self.main_pile = Pile([Divider(),
                               Text(('subheading', "Machine Placement"),
                                    align='center'),
                               Divider(),
                               Padding(self.columns,
                                       align='center',
                                       width=('relative', 95))])
        return Filler(self.main_pile, valign='top')

    def update(self):
        self.services_column.update()
        self.machines_column.update()

    def do_autoplace(self, sender):
        ok, msg = self.placement_controller.autoplace_unplaced_services()
        if not ok:
            self.show_overlay(InfoDialog(msg, self.remove_overlay))

    def do_clear_all(self, sender):
        self.placement_controller.clear_all_assignments()

    def do_clear_machine(self, sender, machine):
        self.placement_controller.clear_assignments(machine)

    def do_show_service_chooser(self, sender, machine):
        self.show_overlay(ServiceChooser(self.placement_controller,
                                         machine,
                                         self))

    def do_show_machine_chooser(self, sender, charm_class):
        self.show_overlay(MachineChooser(self.placement_controller,
                                         charm_class,
                                         self))

    def show_overlay(self, overlay_widget):
        self.orig_w = self._w
        self._w = Overlay(top_w=overlay_widget,
                          bottom_w=self._w,
                          align='center',
                          width=('relative', 60),
                          min_width=80,
                          valign='middle',
                          height='pack')

    def remove_overlay(self, overlay_widget):
        # urwid note: we could also get orig_w as
        # self._w.contents[0][0], but this is clearer:
        self._w = self.orig_w
