#
# gui.py - Cloud install gui components
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

""" Pegasus - gui interface to  Installer """

from __future__ import unicode_literals
from operator import attrgetter
import re
import logging
import functools

from urwid import (AttrWrap, AttrMap, Text, Columns, Overlay, LineBox,
                   ListBox, Filler, Button, BoxAdapter, Frame, WidgetWrap,
                   RadioButton, IntEdit, SimpleListWalker, Padding)

from cloudinstall import utils
from cloudinstall.ui import StatusBar, StepInfo

log = logging.getLogger('cloudinstall.gui')

TITLE_TEXT = "Ubuntu Openstack Installer"

# - Properties ----------------------------------------------------------------
IS_TTY = re.match('/dev/tty[0-9]', utils.get_command_output('tty')['stdout'])

# Time to lock in seconds
LOCK_TIME = 120

padding = functools.partial(Padding, left=2, right=2, top=2, bottom=2)


class AddCharmDialog(WidgetWrap):
    """ Adding charm dialog """

    def __init__(self, charm_classes, **kwargs):
        self.boxes = []
        self.bgroup = []
        first_index = 0
        for i, charm_class in enumerate(charm_classes):
            charm = charm_class
            if charm.name() and not first_index:
                first_index = i
            r = RadioButton(self.bgroup, charm.name())
            r.text_label = charm.name()
            self.boxes.append(r)

        self.count_editor = IntEdit("Number of units to add: ", 1)
        self.boxes.append(self.count_editor)
        wrapped_boxes = self._wrap_focus(self.boxes)

        bs = [Button("Ok", self.yes), Button("Cancel", self.no)]
        wrapped_buttons = self._wrap_focus(bs)
        self.buttons = Columns(wrapped_buttons)
        self.items = ListBox(wrapped_boxes)
        self.items.set_focus(first_index)
        ba = BoxAdapter(self.items, height=len(wrapped_boxes))
        self.lb = ListBox([ba, Text(""), self.buttons])
        self.w = LineBox(self.lb, title="Add unit")
        self.w = AttrMap(self.w, "dialog")
        super().__init__(self.w)

    def yes(self, button):
        #selected = [r for r in self.boxes if
        #            r is not self.count_editor
        #            and r.get_state()][0]
        #_charm_to_deploy = selected.label
        #n = self.count_editor.value()
        pass

    def _wrap_focus(widgets, unfocused=None):
        try:
            return [AttrMap(w, unfocused, "focus") for w in widgets]
        except TypeError:
            return AttrMap(widgets, unfocused, "focus")


class Banner(WidgetWrap):
    def __init__(self):
        self.text = []
        self.BANNER = [
            "",
            """
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMNdmMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMM+   .mMMMMMMMMMM
MMMMMMMMMMMMMMMy+/---:/m-    dMMMMMMMMMM
MMMMMMMMMMMNs/Ns       .ssosmMMMMMMMMMMM
MMMMMMMMMMy`  .mhhdmmdy+.   .hMMMMMMMMMM
MMMMMMMMMo   -dMMMMMMMMMMh.   yMMMMMMMMM
MMMMMhydm`  -MMMMMMMMMMMMMN.  `mMMMMMMMM
MMMm`   :m  dMMMMMMMMMMMMMMh///hMMMMMMMM
MMMm`   -m  dMMMMMMMMMMMMMMh///hMMMMMMMM
MMMMNhydm`  :MMMMMMMMMMMMMN.   mMMMMMMMM
MMMMMMMMMo   -dMMMMMMMMMMh.   yMMMMMMMMM
MMMMMMMMMMy`  `mhhmNmdy+.   .hMMMMMMMMMM
MMMMMMMMMMMNo:ms       .ssosmMMMMMMMMMMM
MMMMMMMMMMMMMMMy+:----/m-    dMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMM/   .mMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMNdmMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
""",
            "",
            "Openstack Installer",
            "",
            "By Canonical, Ltd."
        ]
        super().__init__(self._create_text())

    def _create_text(self):
        self.text = []
        for line in self.BANNER:
            self._insert_line(line)

        return ListBox(SimpleListWalker(self.text))

    def _insert_line(self, line):
        text = Text(line, align='center')
        self.text.append(text)


class NodeViewMode(WidgetWrap):
    def __init__(self, nodes, **kwargs):
        nodes = [] if nodes is None else nodes
        widget = self._build_widget(nodes, **kwargs)
        super().__init__(widget)

    def _build_widget(self, nodes, **kwargs):
        unit_info = []
        for node in nodes:
            for u in sorted(node.units, key=attrgetter('unit_name')):
                info = "\N{TRIANGULAR BULLET} {unit_name} " \
                       "({status})".format(unit_name=u.unit_name,
                                           status=u.agent_state)

                if u.public_address:
                    info += "\naddress: {address}".format(
                        address=u.public_address)

                if 'error' in u.agent_state:
                    state_info = u.agent_state_info.lstrip()
                    info += "\ninfo: {state_info}".format(
                        state_info=state_info)

                # unit_machine = self.juju_state.machine(u.machine_id)
                # if unit_machine.agent_state is None and \
                #    unit_machine.agent_state_info is not None:
                #     info += "\nmachine info: " + unit_machine.agent_state_info

                info += "\n\n"
                unit_info.append(Text(info))

        return ListBox(SimpleListWalker(unit_info))

    def keypress(self, size, key):
        return key


class Header(WidgetWrap):
    def __init__(self):
        header = [AttrWrap(padding(Text(TITLE_TEXT)), "header title"),
                  AttrWrap(padding(Text('(F6) Add units')), "border"),
                  AttrWrap(padding(Text('(F5) Refresh')), "border"),
                  AttrWrap(padding(Text('(Q) Quit')), "border")]
        super().__init__(Columns(header))


class PegasusGUI(WidgetWrap):
    def __init__(self):
        header = Header()
        body = Banner()
        footer = StatusBar('')

        self.frame = Frame(body,
                           header=header,
                           footer=footer)

        super().__init__(self.frame)

    def _build_overlay_widget(self,
                              top_w,
                              align,
                              width,
                              valign,
                              height,
                              min_width,
                              min_height):
        return Overlay(top_w=Filler(top_w),
                       bottom_w=self.frame,
                       align=align,
                       width=width,
                       valign=valign,
                       height=height,
                       min_width=width,
                       min_height=height)

    def show_widget_on_top(self,
                           widget,
                           width,
                           height,
                           align='center',
                           valign='middle',
                           min_height=0,
                           min_width=0):
        """Show `widget` on top of :attr:`frame`."""
        self._w = self._build_overlay_widget(top_w=widget,
                                             align=align,
                                             width=width,
                                             valign=valign,
                                             height=height,
                                             min_width=min_width,
                                             min_height=min_height)

    def hide_widget_on_top(self):
        """Hide the topmost widget (if any)."""
        self._w = self.frame

    def show_step_info(self, msg=None):
        self.hide_step_info()
        widget = StepInfo(msg)
        self.show_widget_on_top(widget, width=50, height=10)

    def hide_step_info(self):
        self.hide_widget_on_top()

    def show_add_charm_info(self, charms):
        widget = AddCharmDialog(charms)
        self.show_widget_on_top(widget, width=50, height=20)

    def hide_add_charm_info(self):
        self.hide_widget_on_top()

    def status_message(self, text):
        self.frame.footer.message(text)
        self.frame.set_footer(self.frame.footer)

    def status_error_message(self, message):
        self.frame.footer.error_message(message)

    def status_info_message(self, message):
        self.frame.footer.info_message(message)

    def clear_status(self):
        self.frame.footer = None
        self.frame.set_footer(self.frame.footer)

    def render_nodes(self, nodes, **kwargs):
        self.frame.body = NodeViewMode(nodes)
        self.frame.set_body(self.frame.body)
