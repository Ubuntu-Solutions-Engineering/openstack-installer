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
from urwid import (AttrWrap, Columns, LineBox,
                   ListBox, BoxAdapter, WidgetWrap,
                   RadioButton, SimpleListWalker, Divider, Button,

                   signals, emit_signal, connect_signal)
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


class Selector(WidgetWrap):

    """
    Simple selector box

    :param str title: title of selections
    :param list opts: items to select
    :param cb: callback
    :returns: item selected from dialog
    """
    __metaclass__ = signals.MetaSignals
    signals = ['done']

    def __init__(self, title, opts, cb, **kwargs):
        self.opts = opts
        self.title = title
        self.cb = cb
        self.boxes = []
        self.items = []

        w = self._build_widget()
        w = AttrWrap(w, 'dialog')

        connect_signal(self, 'done', self.cb)
        super().__init__(w)

    def submit(self, button):
        selected = [r for r in self.boxes if r.get_state()][0]
        selected_item = selected.label
        self.emit_done_signal(selected_item)

    def cancel(self, button):
        raise SystemExit("Installation Cancelled.")

    def emit_done_signal(self, *args):
        emit_signal(self, 'done', *args)

    def _build_widget(self, **kwargs):
        num_of_items, item_sel = self._insert_item_selections()
        buttons = self._insert_buttons()
        return LineBox(
            BoxAdapter(
                ListBox([item_sel, Divider(), buttons]),
                height=num_of_items + 2),
            title=self.title)

    def keypress(self, size, key):
        if key != 'tab':
            super().keypress(size, key)
        if key == 'tab':
            old_widget, old_pos = self.items.get_focus()
            self.items.set_focus((old_pos + 1) % len(self.boxes))

    def _insert_item_selections(self):
        bgroup = []
        for i, item in enumerate(self.opts):
            r = RadioButton(bgroup, item)
            r.text_label = item
            self.boxes.append(r)

        wrapped_boxes = self._wrap_radio_focus(self.boxes)

        self.items = ListBox(SimpleListWalker(wrapped_boxes))
        self.items.set_focus(0)
        return (len(self.boxes), BoxAdapter(self.items, len(self.boxes)))

    def _insert_buttons(self):
        bs = [AttrWrap(Button("Start install", self.submit),
                       'button', 'button focus'),
              AttrWrap(Button("Cancel", self.cancel),
                       'button', 'button focus')]
        return Columns(bs)

    def _wrap_radio_focus(self, widgets, unfocused=None):
        try:
            return [AttrWrap(w, "input", "input focus") for w in widgets]
        except TypeError:
            return AttrWrap(widgets, "input", "input focus")


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
        self.add_input('lds_admin_email', 'Admin Email: ')
        self.add_input('lds_admin_name', 'Admin Name: ')
        self.add_input('lds_system_email', 'System Email: ')
        self.add_input('maas_server', 'MAAS Server IP (optional): ')
        self.add_input('maas_server_key', 'MAAS API Key (optional): ')
        self.show()
