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

from __future__ import unicode_literals
import logging
from urwid import (Text, WidgetWrap, Filler,
                   Pile, Divider, Button)
from cloudinstall.ui.utils import Color, Padding

log = logging.getLogger('cloudinstall.stepinf')


class StepInfoView(WidgetWrap):

    def __init__(self, msg=None):
        if not msg:
            msg = "Processing."
        items = [
            Padding.center_60(Text("Information", align="center")),
            Padding.center_60(
                Divider("\N{BOX DRAWINGS LIGHT HORIZONTAL}", 1, 1)),
            Padding.center_60(Text(msg))
        ]
        super().__init__(Filler(Pile(items), valign='middle'))

    def _build_buttons(self):
        buttons = [
            Padding.line_break(""),
            Color.button_secondary(
                Button("Quit", self.cancel),
                focus_map='button_secondary focus'),
        ]
        return Pile(buttons)

    def cancel(self, button):
        raise SystemExit("Installation cancelled.")
