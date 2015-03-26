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


from urwid import (AttrMap, Button, GridFlow,
                   Padding, Pile, SelectableIcon, Text, WidgetWrap)

from cloudinstall.utils import format_constraint
from cloudinstall.state import CharmState


class ServiceWidget(WidgetWrap):

    """A widget displaying a service and associated actions.

    charm_class - the class describing the service to display

    controller - a PlacementController instance

    actions - a list of ('label', function) pairs that will be used to
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
                 show_constraints=False, show_assignments=False):
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

        state, cons, deps = self.controller.get_charm_state(self.charm_class)

        if state == CharmState.REQUIRED:
            np = self.controller.machine_count_for_charm(self.charm_class)
            nr = self.charm_class.required_num_units()
            info_str = " ({} of {} placed)".format(np, nr)

            # Add hint to explain why a dep showed up in required
            if np == 0 and len(deps) > 0:
                dep_str = ", ".join([c.display_name for c in deps])
                info_str += " - required by {}".format(dep_str)

            self.title_markup[1] = ('info', info_str)
            self.charm_info_widget.set_text(self.title_markup)

        elif state == CharmState.CONFLICTED:
            con_str = ", ".join([c.display_name for c in cons])
            self.title_markup[1] = ('error_icon',
                                    ' - Conflicts with {}'.format(con_str))
            self.charm_info_widget.set_text(self.title_markup)
        elif state == CharmState.OPTIONAL:
            self.title_markup[1] = ""
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
                def predicate(x):
                    return True
                label, func = at
            else:
                predicate, label, func = at

            if not predicate(self.charm_class):
                b = AttrMap(SelectableIcon(" (" + label + ")"),
                            'disabled_button', 'disabled_button_focus')
            else:
                b = AttrMap(Button(label, on_press=func,
                                   user_data=self.charm_class),
                            'button_secondary', 'button_secondary focus')
            buttons.append((b, self.button_grid.options()))

        self.button_grid.contents = buttons
