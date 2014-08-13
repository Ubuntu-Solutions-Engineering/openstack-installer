#!/usr/bin/env python3
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

""" Provides interface to viewing separate gui components without
    running through a full installation
"""

import sys
import os
sys.path.insert(0, '../cloudinstall')

from cloudinstall import gui, log
from cloudinstall.core import DisplayController
from cloudinstall.config import Config
from cloudinstall.juju import JujuState
from macumba import JujuClient

class FakeOpts:
    noui = False
    enable_swift = False

if __name__ == '__main__':
    log.setup_logger()
    ui = DisplayController(ui=gui.PegasusGUI(),
                           opts=FakeOpts())
    sys.exit(ui.start())
