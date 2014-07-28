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

from urwid import Overlay, LineBox, ListBox, Text, AttrWrap


HELP_TEXT = ["""Press Enter to remove this dialog.

For full documentation, please refer to
http://ubuntu-cloud-installer.readthedocs.org/en/latest/

""",
             ('bold', "Overview"),
             """

- Header

The header shows a few common command keys for quick reference.

- Main Table

The main table has a row for each Juju service in the current
environment. It is updated every ten seconds. The first column shows
the name of the service, and the remaining columns show an entry for
each unit in the following form:

servicename/unitnumber (status)
address: unit IP address

There may also be a "machine info" field with information in the event
of provisioning errors.

- Footer

The footer displays a status message, and the URLs for the two web
dashboards installed, one for OpenStack Horizon and the other for the
Juju GUI.

""",
             ('bold', "Command Reference"),
             """

- F5 refreshes the displayed state immediately

- F6 brings up a dialog box for adding additional units. This is how
  to add compute units or a storage service. This dialog takes care of
  launching required dependencies, so for example, launching swift
  here will add a swift-proxy service and enough swift-storage nodes
  to meet the replica criterion (currently 3).

- '?' displays this help screen.

- 'q' quits.

""",

             ('bold', "Troubleshooting"),
             """

The juju commands used to deploy the services listed are logged in
~/.cloud-install/commands.log

* In a multi-install, MAAS may return a "409 CONFLICT" error, which
will be shown with the label "machine info" under the unit name in the
main table. This indicates a failure to find a machine that matches
the default constraints set for the service. See the log file for
details.
""",
             ('bold', "End of Help Screen")]


class ScrollableListBox(ListBox):
    def focus_next(self):
        try:
            self.body.set_focus(self.body.get_next(
                self.body.get_focus()[1])[1])
        except:
            pass

    def focus_previous(self):
        try:
            self.body.set_focus(self.body.get_prev(
                self.body.get_focus()[1])[1])
        except:
            pass


class HelpScreen(Overlay):
    def __init__(self, underlying, remove_func):
        self.remove_func = remove_func
        tl = [Text(t) for t in HELP_TEXT]
        self.listbox = ScrollableListBox(tl)
        w = LineBox(self.listbox, title="Help (scroll with up/down arrows)")
        w = AttrWrap(w, "dialog")
        Overlay.__init__(self, w, underlying,
                         'center', 72,
                         'middle', ('relative', 66),
                         min_width=80,
                         min_height=60)

    def keypress(self, size, key):
        if key == 'enter':
            self.remove_func()
            return None
        if key == 'up':
            self.listbox.focus_previous()
        if key == 'down':
            self.listbox.focus_next()
        else:
            return Overlay.keypress(self, size, key)
