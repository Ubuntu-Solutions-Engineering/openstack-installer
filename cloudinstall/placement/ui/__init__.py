# Copyright 2014, 2015 Canonical, Ltd.
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

from urwid import (AttrMap, Button, Columns, Divider, Filler,
                   GridFlow, Overlay, Padding, Pile, SelectableIcon,
                   Text, WidgetWrap)

from cloudinstall.placement.controller import AssignmentType

from cloudinstall.placement.ui.machine_chooser import MachineChooser
from cloudinstall.placement.ui.machines_list import MachinesList
from cloudinstall.placement.ui.service_chooser import ServiceChooser
from cloudinstall.placement.ui.services_list import ServicesList
from cloudinstall.ui.widgets import InfoDialogWidget
from cloudinstall.state import CharmState

log = logging.getLogger('cloudinstall.placement')


BUTTON_SIZE = 20


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

        def not_conflicted_p(cc):
            state, _, _ = self.placement_controller.get_charm_state(cc)
            return state != CharmState.CONFLICTED

        actions = [(not_conflicted_p, "Choose Machine",
                    self.placement_view.do_show_machine_chooser)]
        subordinate_actions = [(not_conflicted_p, "Add",
                                self.do_place_subordinate)]
        self.required_services_list = ServicesList(self.placement_controller,
                                                   actions,
                                                   subordinate_actions,
                                                   ignore_assigned=True,
                                                   ignore_deployed=True,
                                                   show_type='required',
                                                   show_constraints=True,
                                                   title="Required Services")
        self.additional_services_list = ServicesList(self.placement_controller,
                                                     actions,
                                                     subordinate_actions,
                                                     ignore_assigned=True,
                                                     show_type='non-required',
                                                     show_constraints=True,
                                                     title="Additional "
                                                     "Services")

        autoplace_func = self.placement_view.do_autoplace
        self.autoplace_button = AttrMap(Button("Auto-place Remaining Services",
                                               on_press=autoplace_func),
                                        'button_secondary',
                                        'button_secondary focus')

        clear_all_func = self.placement_view.do_clear_all
        self.clear_all_button = AttrMap(Button("Clear All Placements",
                                               on_press=clear_all_func),
                                        'button_secondary',
                                        'button_secondary focus')

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
        unplaced = self.placement_controller.unassigned_undeployed_services()
        if len(unplaced) == 0:
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

    def do_place_subordinate(self, sender, charm_class):
        sub_placeholder = self.placement_controller.sub_placeholder
        self.placement_controller.assign(sub_placeholder,
                                         charm_class,
                                         AssignmentType.BareMetal)


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
        self.deploy_ok_msg = ("\u2713 All the required OpenStack services are "
                              "placed on a machine, and you can now deploy.")

        self.deploy_button = AttrMap(
            Button("Deploy", on_press=self.do_deploy),
            'button_primary', 'button_primary focus')
        self.deploy_grid = GridFlow([self.deploy_button], 10, 1, 0, 'center')

        self.unplaced_msg = "Some required services are still unassigned."

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
                self.display_controller.status_error_message(self.unplaced_msg)

        self.prev_status = self.placement_controller.can_deploy()

    def show_deploy_button(self):
        self.main_pile.contents[0] = (AttrMap(self.deploy_grid,
                                              'deploy_highlight_start'),
                                      self.main_pile.options())

        # XXX: What was this for?
        # def fade_timeout(loop, step):
        #     if step == 1:
        #         self.loop.set_alarm_in(5, 2)
        #         new_attr = 'deploy_highlight_end'
        #     else:
        #         new_attr = ''
        #     self.main_pile.contents[0] = (AttrMap(self.deploy_grid,
        #                                           new_attr),
        #                                   self.main_pile.options())
        # self.loop.set_alarm_in(4, 1)
        self.display_controller.status_info_message(self.deploy_ok_msg)

    def do_deploy(self, sender):
        self.placement_view.do_deploy_cb()


class MachinesColumn(WidgetWrap):

    """Shows machines or a link to MAAS to add more"""

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

        def has_services_p(m):
            pc = self.placement_controller
            n = sum([len(al) for at, al in
                     pc.assignments_for_machine(m).items()])
            return n > 0

        clear_machine_func = self.placement_view.do_clear_machine
        show_chooser_func = self.placement_view.do_show_service_chooser

        self.open_maas_button = AttrMap(Button("Open in Browser",
                                               on_press=self.browse_maas),
                                        'button_secondary',
                                        'button_secondary focus')

        bc = self.placement_view.config.juju_env['bootstrap-config']
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

        bc = self.placement_view.config.juju_env['bootstrap-config']
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

        # 1 machine is the subordinate placeholder:
        if len(self.placement_controller.machines()) == 1:
            self.main_pile.contents[2] = (self.empty_maas_widgets,
                                          self.main_pile.options())
        else:
            self.main_pile.contents[2] = (self.machines_list_pile,
                                          self.main_pile.options())

    def browse_maas(self, sender):

        bc = self.placement_view.config.juju_env['bootstrap-config']
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

        w = InfoDialogWidget(msg, self.placement_view.remove_overlay)
        self.placement_view.show_overlay(w)


class PlacementView(WidgetWrap):

    """
    Handles display of machines and services.

    displays nothing if self.controller is not set.
    set it to a PlacementController.

    :param do_deploy_cb: deploy callback from controller
    """

    def __init__(self, display_controller, placement_controller,
                 loop, config, do_deploy_cb):
        self.display_controller = display_controller
        self.placement_controller = placement_controller
        self.loop = loop
        self.config = config
        self.do_deploy_cb = do_deploy_cb
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
        ok, msg = self.placement_controller.autoassign_unassigned_services()
        if not ok:
            self.show_overlay(InfoDialogWidget(msg, self.remove_overlay))

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
