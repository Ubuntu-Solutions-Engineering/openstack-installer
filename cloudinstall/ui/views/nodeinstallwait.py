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

import random
from urwid import (WidgetWrap, Text, Filler, Pile, Columns)
from cloudinstall.ui.utils import Padding


class NodeInstallWaitView(WidgetWrap):

    load_attributes = [('pending_icon', "\u2581"),
                       ('pending_icon', "\u2582"),
                       ('pending_icon', "\u2583"),
                       ('pending_icon', "\u2584"),
                       ('pending_icon', "\u2585"),
                       ('pending_icon', "\u2586"),
                       ('pending_icon', "\u2587"),
                       ('pending_icon', "\u2588")]

    def __init__(self,
                 message="Installer is initializing nodes. Please wait."):
        self.message = Text(message, align="center")
        self.loading_boxes = [Text(x) for x in self.load_attributes]
        super().__init__(self._build_node_waiting())

    def redraw_kitt(self):
        """ Redraws the KITT bar
        """
        random.shuffle(self.load_attributes)
        for i in self.loading_boxes:
            i.set_text(
                self.load_attributes[random.randrange(
                    len(self.load_attributes))])

    def _build_node_waiting(self):
        """ creates a loading screen if nodes do not exist yet """
        text = [Padding.line_break(""),
                self.message,
                Padding.line_break("")]

        _boxes = []
        _boxes.append(('weight', 1, Text('')))
        for i in self.loading_boxes:
            _boxes.append(('pack', i))
        _boxes.append(('weight', 1, Text('')))
        _boxes = Columns(_boxes)

        return Filler(Pile(text + [_boxes]),
                      valign="middle")
