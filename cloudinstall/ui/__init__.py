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
from urwid import WidgetWrap, Text, AttrWrap, LineBox


class StatusBar(WidgetWrap):
    """Displays text."""

    INFO = "[INFO]"
    ERROR = "[ERROR]"
    ARROW = " \u21e8 "

    def __init__(self, text=''):
        super().__init__(Text(text))

    def message(self, text):
        """Write `text` on the footer."""
        self._w.set_text(text)

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
