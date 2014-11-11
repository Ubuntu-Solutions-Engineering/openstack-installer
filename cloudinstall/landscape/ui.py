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

import logging
from urwid import (Button, Pile, Text, WidgetWrap)


log = logging.getLogger('cloudinstall.install')


class LandscapeMachineView(WidgetWrap):
    def __init__(self, display_controller, installer):
        self.display_controller = display_controller
        self.installer = installer
        w = self.build_widgets()
        super().__init__(w)
        self.update()

    def build_widgets(self):
        self.message = Text("Please review available machines in MAAS")
        self.status_pile = Pile()
        # TODO disable continue button until OK to continue
        self.continue_button = Button('Continue',
                                      on_press=self.installer.do_install)
        self.main_pile = Pile([self.message, self.status_pile,
                               self.continue_button])
        return self.main_pile

    def get_status(self):
        " returns (global_ok, [ok, condition])"
        return [(True, "6 machines up"),
                (False, "At least one with 2 nics available for OpenStack")]

    def update(self):
        # temp
        import time
        self.message = Text("{:.2f}".format(time.time()))
        global_ok, statuses = self.get_status()
        contents = [(Text([('label', status), condition]),
                     self.status_pile.options())
                    for status, condition
                    in statuses]
        self.status_pile.contents = contents
        # TODO update button state
