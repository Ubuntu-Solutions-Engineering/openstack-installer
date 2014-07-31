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
import re
import logging
import functools

from urwid import (AttrWrap, Text, Columns, Overlay, LineBox,
                   ListBox, Filler, Button, BoxAdapter, Frame, WidgetWrap,
                   RadioButton, IntEdit, Padding, Pile)
from cloudinstall import utils
from cloudinstall.ui import (ScrollableWidgetWrap,
                             ScrollableListBox)
from cloudinstall.ui.helpscreen import HelpScreen

log = logging.getLogger('cloudinstall.gui')

TITLE_TEXT = "Ubuntu Openstack Installer - Dashboard"

# - Properties ----------------------------------------------------------------
IS_TTY = re.match('/dev/tty[0-9]', utils.get_command_output('tty')['stdout'])

# Time to lock in seconds
LOCK_TIME = 120

padding = functools.partial(Padding, left=2, right=2)


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
        w = LineBox(self.lb, title="Add unit")
        w = AttrWrap(w, "dialog")
        super().__init__(Columns(self.items))

    def yes(self, button):
        #selected = [r for r in self.boxes if
        #            r is not self.count_editor
        #            and r.get_state()][0]
        #_charm_to_deploy = selected.label
        #n = self.count_editor.value()
        pass

    def no(self, button):
        pass

    def _wrap_focus(self, widgets, unfocused=None):
        try:
            return [AttrWrap(w, "focus") for w in widgets]
        except TypeError:
            return AttrWrap(widgets, "focus")


class Banner(ScrollableWidgetWrap):
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

        return ScrollableListBox(self.text)

    def _insert_line(self, line):
        text = Text(line, align='center')
        self.text.append(text)


class NodeViewMode(ScrollableWidgetWrap):
    def __init__(self, nodes, **kwargs):
        nodes = [] if nodes is None else nodes
        widget = self._build_widget(nodes, **kwargs)
        super().__init__(widget)

    def _build_widget(self, nodes, **kwargs):
        unit_info = []
        for node in nodes:
            node_pile = []
            charm, node, state = node
            if charm.menuable:
                for u in node.units:
                    machine = state.machine(u.machine_id)
                    if u.agent_state == "error":
                        status = ("error_icon", "\N{BULLET} ")
                    else:
                        status = ("success_icon", "\u2713 ")
                    node_pile.append(('pack', Text(status)))
                    if u.public_address:
                        node_pile.append(
                            ('pack',
                             Text(u.public_address)))

                    if 'error' in u.agent_state:
                        state_info = u.agent_state_info.lstrip()
                        node_pile.append(Text(" Info: "
                                              "{state_info}".format(
                                                  state_info=state_info)))
                    node_pile.append(Text(" \u2022 arch={0} mem={1} "
                                          "storage={2}".format(
                                              machine.arch,
                                              machine.mem,
                                              machine.storage
                                          )))
                    node_pile = [Columns(node_pile)]

                unit_info.append(padding(LineBox(
                    Pile(node_pile),
                    title=charm.display_name)))

        return ScrollableListBox(unit_info)

    def keypress(self, size, key):
        return key


class Header(WidgetWrap):
    def __init__(self):
        w = []
        w.append(AttrWrap(padding(Text(TITLE_TEXT)), "header_title"))
        w.append(AttrWrap(Columns([
            ('pack', AttrWrap(Text('(F6) Add units', align='center'),
                              'button')),
            (18, AttrWrap(Text('(F5) Refresh', align='center'), 'button')),
            ('pack', AttrWrap(Text('(Q) Quit', align='center'), 'button'))
        ]), "border"))
        w = Pile(w)
        super().__init__(w)


class StatusBar(WidgetWrap):
    """Displays text."""

    INFO = "[INFO]"
    ERROR = "[ERROR]"
    ARROW = " \u21e8 "

    def __init__(self, text=''):
        self._status_line = Text(text)
        self._horizon_url = Text('')
        self._jujugui_url = Text('')
        self._openstack_rel = Text('Icehouse (2014.1.1)')
        self._status_extra = self._build_status_extra()
        status = Pile([self._status_line, self._status_extra])
        super().__init__(status)

    def _build_status_extra(self):
        status = []
        status.append(self._horizon_url)
        status.append(self._jujugui_url)
        status.append(('pack', self._openstack_rel))
        return AttrWrap(Columns(status), 'status_extra')

    def set_dashboard_url(self, ip=None):
        """ sets horizon dashboard url """
        text = "Openstack Dashboard: "
        if not ip:
            text += "(pending)"
        else:
            text += "http://{}/".format(ip)
        return self._horizon_url.set_text(text)

    def set_jujugui_url(self, ip=None):
        """ sets juju gui url """
        text = "JujuGUI: "
        if not ip:
            text += "(pending)"
        else:
            text += "http://{}/".format(ip)
        return self._jujugui_url.set_text(text)

    def message(self, text):
        """Write `text` on the footer."""
        self._status_line.set_text(text)

    def error_message(self, text):
        self.message([('error', self.ERROR),
                      ('default', self.ARROW + text)])

    def info_message(self, text):
        self.message([('info', self.INFO),
                      ('default', self.ARROW + text)])

    def clear(self):
        """Clear the text."""
        self._w.set_text('')


class StepInfo(WidgetWrap):
    def __init__(self, msg=None):
        if not msg:
            msg = "Processing."
        super().__init__(AttrWrap(LineBox(Text(msg)), 'dialog'))


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

    def focus_next(self):
        self.frame.body.scroll_down()

    def focus_previous(self):
        self.frame.body.scroll_up()

    def focus_first(self):
        self.frame.body.scroll_top()

    def focus_last(self):
        self.frame.body.scroll_bottom()

    def hide_widget_on_top(self):
        """Hide the topmost widget (if any)."""
        self._w = self.frame

    def show_help_info(self):
        widget = HelpScreen()
        self.show_widget_on_top(widget, width=80, height=20)

    def hide_help_info(self):
        self.hide_widget_on_top()

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

    def status_dashboard_url(self, ip):
        self.frame.footer.set_dashboard_url(ip)

    def status_jujugui_url(self, ip):
        self.frame.footer.set_jujugui_url(ip)

    def clear_status(self):
        self.frame.footer = None
        self.frame.set_footer(self.frame.footer)

    def render_nodes(self, nodes, **kwargs):
        self.frame.body = NodeViewMode(nodes)
        self.frame.set_body(self.frame.body)
