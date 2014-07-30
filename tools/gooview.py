#!/usr/bin/env python
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

from cloudinstall import gui
from cloudinstall.core import BaseController
from cloudinstall.config import Config
from cloudinstall.juju import JujuState
from macumba import JujuClient

if __name__ == '__main__':
    cfg = Config()
    ui = BaseController(ui=gui.PegasusGUI())
    ui.juju = JujuClient(
        url=os.path.join('wss://',
                         cfg.juju_env['state-servers'][0]),
        password=cfg.juju_api_password)
    ui.juju.login()
    ui.juju_state = JujuState(ui.juju)
    sys.exit(ui.start())
