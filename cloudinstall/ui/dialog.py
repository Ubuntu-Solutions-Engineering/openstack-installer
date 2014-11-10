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
    key_conversion_map = {'tab': 'down', 'shift tab': 'up'}

    def __init__(self, title, cb):
        self.title = title
        self.cb = cb
        self.input_items = OrderedDict()
        self.input_lbox = []
        self.container_lbox = []

    def show(self):
        w = self._build_widget()
        w = AttrWrap(w, 'dialog')

        connect_signal(self, 'done', self.cb)
        super().__init__(w)

    def keypress(self, size, key):
        key = self.key_conversion_map.get(key, key)
        if key == 'down':
            old_pos = self.container_lbox.focus
            log.debug("Old focus item: {}".format(old_pos))
            if old_pos == self.btn_columns:
                if self.btn_columns.focus_position == 0:
                    self.btn_columns.set_focus(self.btn_cancel)
        elif key == 'up':
            old_pos = self.container_lbox.focus
            if old_pos == self.btn_columns:
                # This should work as if cancel button
                # is old_pos during shift tab
                # we should go back to the ok button
                if old_pos.focus_position == 1:
                    log.debug("Hit cancel position: {}".format(old_pos))
                    self.btn_columns.set_focus(self.btn_ok)
        return super().keypress(size, key)

    def add_buttons(self):
        """ Adds default OK/Cancel buttons for dialog
        """
        self.btn_ok = AttrWrap(Button("Ok", self.submit),
                               'button', 'button focus')
        self.btn_cancel = AttrWrap(Button("Cancel", self.cancel),
                                   'button', 'button focus')
        self.btn_columns = Columns([self.btn_ok, self.btn_cancel])

    def add_input(self, key, caption, **kwargs):
        """ Adds input boxes while setting their label attributes for
        easy retrieval of data

        :param str caption: viewable label of input
        :param dict **kwargs: additional Edit attributes
        """
        edit = EditInput(caption=caption, **kwargs)
        self.input_items[key] = edit

    def add_radio(self, item, group=[]):
        """ Adds radio selections
        """
        r = RadioButton(group, item)
        r.text_label = item
        self.input_items[item] = r

    def _build_widget(self, **kwargs):

        def box_adapter(items, box):
            box.set_focus(0)
            return (len(items), BoxAdapter(box, len(items)))

        total_items = []
        for _item in self.input_items.keys():
            total_items.append(AttrWrap(
                self.input_items[_item], 'input', 'input focus'))
        self.input_lbox = ListBox(SimpleListWalker(total_items))

        num_of_items, items = box_adapter(total_items,
                                          self.input_lbox)

        log.debug("Num items: {}, items: {}".format(num_of_items,
                                                    items))

        # Add buttons
        self.add_buttons()
        self.container_lbox = ListBox([items, Divider(), self.btn_columns])

        return LineBox(
            BoxAdapter(self.container_lbox,
                       height=num_of_items + 2),
            title=self.title)

    def submit(self, button):
        log.debug("Callback on : {}".format(self.input_items))
        self.emit_done_signal(self.input_items)

    def cancel(self, button):
        raise SystemExit("Installation cancelled.")

    def emit_done_signal(self, *args):
        emit_signal(self, 'done', *args)
