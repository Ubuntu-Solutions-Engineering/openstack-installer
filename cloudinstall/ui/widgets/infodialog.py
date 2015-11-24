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

from urwid import (WidgetWrap, Button, LineBox, Pile, Text)


class InfoDialogWidget(WidgetWrap):

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
