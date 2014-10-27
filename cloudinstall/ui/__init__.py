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

import logging
from urwid import (AttrWrap, BoxAdapter, Button, Columns, Divider,
                   LineBox, ListBox, Pile, RadioButton,
                   SimpleListWalker, Text, WidgetWrap, connect_signal,
                   emit_signal, signals)
from cloudinstall.ui.dialog import Dialog

log = logging.getLogger('cloudinstall.ui')


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


class InfoDialog(WidgetWrap):

    """A widget that displays a message and a close button."""

    def __init__(self, message, close_func):
        self.close_func = close_func
        button = Button("Close", self.do_close)
        box = LineBox(Pile([Text(message),
                            button]),
                      title="Info")
        super().__init__(box)

    def do_close(self, sender):
        self.close_func(self)


class Selector(Dialog):

    """
    Simple selector box

    :param str title: title of selections
    :param list opts: items to select
    :param cb: callback
    :returns: item selected from dialog
    """

    def __init__(self, title, opts, cb):
        super().__init__(title, cb)
        for item in opts:
            self.add_radio(item)
        self.show()

    def submit(self, button):
        selected = [r for r in self.total_items if r.get_state()][0]
        selected_item = selected.label
        self.emit_done_signal(selected_item)


class PasswordInput(Dialog):

    """ Password input dialog
    """

    def __init__(self, title, cb):
        super().__init__(title, cb)
        self.add_input('Password: ', mask='*')
        self.add_input('Confirm Password: ',
                       mask='*')
        self.show()


class MaasServerInput(Dialog):

    """ Maas Server input dialog
    """

    def __init__(self, title, cb):
        super().__init__(title, cb)
        self.add_input('MAAS IP Address: ')
        self.add_input('MAAS API Key: ')
        self.show()


class LandscapeInput(Dialog):

    """ Landscape input dialog
    """

    def __init__(self, title, cb):
        super().__init__(title, cb)
        self.add_input('Admin Email: ')
        self.add_input('Admin Name: ')
        self.add_input('System Email: ')
        self.add_input('MAAS Server IP (optional): ')
        self.add_input('MAAS API Key (optional): ')
        self.show()
