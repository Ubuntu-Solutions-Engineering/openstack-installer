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

from __future__ import unicode_literals
from urwid import (AttrWrap, Columns, LineBox,
                   ListBox, BoxAdapter, WidgetWrap,
                   RadioButton, SimpleListWalker, Divider, Button,

                   signals, emit_signal, connect_signal)
from collections import OrderedDict
from cloudinstall.ui.input import EditInput

import logging

log = logging.getLogger('cloudinstall.ui.dialog')


""" re-usable dialog widgets """


class Dialog(WidgetWrap):

    __metaclass__ = signals.MetaSignals
    signals = ['done']

    def __init__(self, title, cb):
        self.title = title
        self.cb = cb
        self.input_items = OrderedDict()
        self.input_lbox = []

    def show(self):
        w = self._build_widget()
        w = AttrWrap(w, 'dialog')

        connect_signal(self, 'done', self.cb)
        super().__init__(w)

    def keypress(self, size, key):
        if key == 'tab':
            old_widget, old_pos = self.input_lbox.get_focus()
            self.input_lbox.set_focus((old_pos + 1) % len(
                self.input_items))
        else:
            super().keypress(size, key)

    def add_buttons(self):
        """ Adds default OK/Cancel buttons for dialog
        """
        buttons = [AttrWrap(Button("Ok", self.submit),
                            'button', 'button focus'),
                   AttrWrap(Button("Cancel", self.cancel),
                            'button', 'button focus')]
        return Columns(buttons)

    def add_input(self, key, caption, **kwargs):
        """ Adds input boxes while setting their label attributes for
        easy retrieval of data

        :param str caption: viewable label of input
        :param dict **kwargs: additional Edit attributes
        """
        self.input_items[key] = EditInput(caption=caption, **kwargs)

    def add_radio(self, item, group=[]):
        """ Adds radio selections
        """
        self.input_items[item] = RadioButton(group, item)

    def _build_widget(self, **kwargs):

        def box_adapter(items, box):
            box.set_focus(0)
            return (len(items), BoxAdapter(box, len(items)))

        total_items = []
        for _item in self.input_items.keys():
            total_items.append(AttrWrap(
                self.input_items[_item], 'input', 'input focus'))
        self.input_lbox = ListBox(SimpleListWalker(total_items))

        num_of_items, items = box_adapter(total_items, self.input_lbox)

        log.debug("Num items: {}, items: {}".format(num_of_items, items))
        return LineBox(
            BoxAdapter(ListBox([items, Divider(), self.add_buttons()]),
                       height=num_of_items + 2),
            title=self.title)

    def submit(self, button):
        log.debug("Callback on : {}".format(self.input_items))
        self.emit_done_signal(self.input_items)

    def cancel(self, button):
        raise SystemExit("Installation cancelled.")

    def emit_done_signal(self, *args):
        emit_signal(self, 'done', *args)
