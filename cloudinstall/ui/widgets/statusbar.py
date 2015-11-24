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

from urwid import WidgetWrap, Text, Pile
from cloudinstall.ui.utils import Color


class StatusBarWidget(WidgetWrap):

    """ Displays text in the footers status area."""

    INFO = "[INFO]"
    ERROR = "[ERROR]"
    ARROW = " \u21e8 "

    def __init__(self, text=''):
        self._pending_deploys = Text('')
        self._status_line = Text(text, align="center")
        self._status_extra = self._build_status_extra()
        status = Pile([self._pending_deploys,
                       self._status_extra])
        super().__init__(status)

    def _build_status_extra(self):
        return Color.frame_footer(
            Pile([
                self._status_line
            ]))

    def message(self, text):
        """Write `text` on the footer."""
        self._status_line.set_text(text)

    def error_message(self, text):
        self.message([('status_error', self.ERROR),
                      self.ARROW + text])

    def info_message(self, text):
        self.message([('status_info', self.INFO),
                      self.ARROW + text])

    def set_pending_deploys(self, pending_deploys):
        if len(pending_deploys) > 0:
            msg = "Pending deploys: " + ", ".join(pending_deploys)
            self._pending_deploys.set_text(msg)
        else:
            self._pending_deploys.set_text('')

    def clear(self):
        """Clear the text."""
        self._w.set_text('')
