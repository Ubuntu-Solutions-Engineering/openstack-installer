#
# roles.py - Cloud installer roles
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This package is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import signal
import sys

from cloudinstall import gui
from cloudinstall import pegasus
from cloudinstall import utils

# TODO: Why does this crash?
# pegasus.wait_for_services()

def sig_handler(signum, frame):
    utils.reset_blanking()
    sys.exit()

for sig in (signal.SIGTERM, signal.SIGQUIT, signal.SIGINT, signal.SIGHUP):
    signal.signal(sig, sig_handler)

class Status:
    """ Class for displaying the services state through a UI similar to top
    """
    def get_data():
        pegasus.maas_login()
        return pegasus.poll_state()

    def run(self):
        gui.PegasusGUI(self.get_data).run()
