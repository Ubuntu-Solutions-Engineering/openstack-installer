#
# helpscreen.py - Cloud install gui help screen
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

from __future__ import unicode_literals
from urwid import Text, AttrWrap, LineBox, BoxAdapter
from cloudinstall.ui import ScrollableListBox, ScrollableWidgetWrap


class HelpScreen(ScrollableWidgetWrap):

    def __init__(self):
        self.text = []
        self.HELP_TEXT = [
            """For full documentation, please refer to
http://ubuntu-cloud-installer.readthedocs.org/en/latest/

            """,
            ('header_title', "Overview"),
            """

- Header

The header shows a few common command keys for quick reference.

- Main Table

The main table has a row for each Juju service in the current
environment. It is updated every ten seconds. Each row will contain
a status icon indicator, agent state, ip address, machine type, and
hardware specifications.

There may also be an additional status field with information in the event
of provisioning errors or additional status notifications.

- Footer

The footer displays a status message, and the URLs for the two web
dashboards installed, one for OpenStack Horizon and the other for the
Juju GUI.

            """,
            ('header_title', "Command Reference"),
            """

- (R/F5) refreshes the displayed state immediately

- (A/a/F6) brings up a dialog box for adding additional units. This is how
  to add compute units or a storage service. This dialog takes care of
  launching required dependencies, so for example, launching swift
  here will add a swift-proxy service and enough swift-storage nodes
  to meet the replica criterion (currently 3).

- '(H/h/?)' displays this help screen.

- 'q' quits.

            """,
            ('header_title', "Troubleshooting"),
            """

The juju commands used to deploy the services listed are logged in
~/.cloud-install/commands.log

* In a multi-install, MAAS may be unable to find machines that match
the default constraints set for one of the services the installer
deploys. This will be shown in the table under the service's heading,
along with detail about what those constraints were.

            """,
            ('header_title', "End of Help Screen")]
        w = self._create_text()
        w = AttrWrap(w, 'dialog')
        super().__init__(w)

    def _create_text(self):
        self.text = []
        for line in self.HELP_TEXT:
            self._insert_line(line)
        return LineBox(BoxAdapter(
            ScrollableListBox(self.text),
            height=20),
            title='Help \u21C5 Scroll (ESC) Close')

    def _insert_line(self, line):
        text = Text(line)
        self.text.append(text)
