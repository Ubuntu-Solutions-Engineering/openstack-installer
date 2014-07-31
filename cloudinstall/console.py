#
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

""" console - reports installation via console output bypassing UI entirely.

This is meant for debugging the actual installing of services.

"""

from __future__ import unicode_literals
import logging
import sys

log = logging.getLogger('cloudinstall.console')


class Status:
    """Displays text."""

    INFO = "[INFO]"
    ERROR = "[ERROR]"
    ARROW = " \u21e8 "

    def __init__(self, text=''):
        self.text = text

    def message(self, text):
        """Write `text`"""
        sys.stdout.write(text)

    def error_message(self, text):
        self.message("{0} {1} {2}".format(self.ERROR, self.ARROW, text))

    def info_message(self, text):
        self.message([('info', self.INFO),
                      ('default', self.ARROW + text)])

    def clear(self):
        """Clear the text."""
        self.text = ''


class Console:
    def __init__(self, opts=None):
        self.opts = opts
        self.status = Status()

    def status_message(self, text):
        self.message(text)

    def status_error_message(self, message):
        self.status.error_message(message)

    def status_info_message(self, message):
        self.status.info_message(message)

    def clear_status(self):
        self.status.clear()

    def render_nodes(self, nodes, **kwargs):
        self.message(nodes)
