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
from urwid import (Pile, WidgetWrap, Text,
                   Button, Filler,
                   signals, emit_signal, connect_signal)
from collections import OrderedDict
from cloudinstall.ui.input import EditInput
from cloudinstall.ui.utils import Color, Padding

import logging

log = logging.getLogger('cloudinstall.ui.dialog')


""" re-usable dialog widgets """


class Dialog(WidgetWrap):

    __metaclass__ = signals.MetaSignals
    signals = ['done']
    # key_conversion_map = {'tab': 'down', 'shift tab': 'up'}

    input_items = []

    def __init__(self, title, cb):
        self.title = title
        self.cb = cb
        self.input_selection = OrderedDict()
        connect_signal(self, 'done', self.cb)
        super().__init__(self._build_widget())

    # def keypress(self, size, key):
    #     key = self.key_conversion_map.get(key, key)
    #     return super().keypress(size, key)

    def _build_buttons(self):
        buttons = [
            Padding.line_break(""),
            Color.button_primary(
                Button("Confirm", self.submit),
                focus_map='button_primary focus'),
            Color.button_secondary(
                Button("Cancel", self.cancel),
                focus_map='button_secondary focus'),
        ]
        return Pile(buttons)

    def _build_widget(self, **kwargs):
        total_items = [
            Padding.center_65(Text(self.title, align="center")),
            Padding.line_break("")
        ]
        if self.input_items:
            for item in self.input_items:
                key = item[0]
                caption = item[1]
                try:
                    mask = item[2]
                except:
                    mask = None
                self.input_selection[key] = EditInput(caption=caption,
                                                      mask=mask)

        for item in self.input_selection.keys():
            total_items.append(
                Padding.center_60(
                    Color.string_input(self.input_selection[item],
                                       focus_map="string_input focus")))
            total_items.append(Padding.line_break(""))
        total_items.append(Padding.center_20(self._build_buttons()))
        return Filler(Pile(total_items), valign='middle')

    def submit(self, button):
        self.emit_done_signal(self.input_selection)

    def cancel(self, button):
        raise SystemExit("Installation cancelled.")

    def emit_done_signal(self, *args):
        emit_signal(self, 'done', *args)
