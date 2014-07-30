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

""" re-usable widgets """

from __future__ import unicode_literals
from urwid import (WidgetWrap, Text, AttrWrap, LineBox, ListBox,
                   SimpleListWalker, Pile, Columns)


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


class Scrollable:
    """A interface that makes widgets *scrollable*."""
    def scroll_up(self):
        raise NotImplementedError

    def scroll_down(self):
        raise NotImplementedError

    def scroll_top(self):
        raise NotImplementedError

    def scroll_bottom(self):
        raise NotImplementedError


class ScrollableListBox(ListBox, Scrollable):
    """
    A ``urwid.ListBox`` subclass that implements the
    :class:`~cloudinstall.ui.Scrollable` interface.
    """
    def __init__(self,
                 contents,
                 offset=1):
        """
        Arguments:

        `contents` is a list with the elements contained in the
        `ScrollableListBox`.

        `offset` is the number of position that `scroll_up` and `scroll_down`
        shift the cursor.
        """
        self.offset = offset

        ListBox.__init__(self,
                         SimpleListWalker(contents))

    def scroll_up(self):
        focus_status, pos = self.get_focus()
        if pos is None:
            return

        new_pos = pos - self.offset
        if new_pos < 0:
            new_pos = 0
        self.set_focus(new_pos)

    def scroll_down(self):
        focus_status, pos = self.get_focus()
        if pos is None:
            return

        new_pos = pos + self.offset
        if new_pos >= len(self.body):
            new_pos = len(self.body) - 1
        self.set_focus(new_pos)

    def scroll_top(self):
        if len(self.body):
            self.set_focus(0)

    def scroll_bottom(self):
        last = len(self.body) - 1
        if last:
            self.set_focus(last)


class ScrollableWidgetWrap(WidgetWrap, Scrollable):
    """
    A ``urwid.WidgetWrap`` for :class:`~cloudinstall.ui.Scrollable`, list-like
    widgets.
    """
    def __init__(self, contents=None):
        columns = [] if contents is None else contents
        WidgetWrap.__init__(self, columns)

    def scroll_up(self):
        self._w.scroll_up()

    def scroll_down(self):
        self._w.scroll_down()

    def scroll_top(self):
        self._w.scroll_top()

    def scroll_bottom(self):
        self._w.scroll_bottom()
