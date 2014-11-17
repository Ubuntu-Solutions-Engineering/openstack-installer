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
import os
import random
from urwid import (AttrMap, Button, Divider, Filler, GridFlow, Pile,
                   SelectableIcon, Text, WidgetWrap)

from cloudinstall.config import Config
from cloudinstall.landscape.lshw import LSHWParser
from cloudinstall.maas import connect_to_maas, FakeMaasState, MaasMachineStatus
from cloudinstall import utils

log = logging.getLogger('cloudinstall.install')


class LandscapeMachineView(WidgetWrap):
    def __init__(self, display_controller, installer):
        self.display_controller = display_controller
        self.installer = installer
        self.config = Config()
        creds = self.config.maas_creds
        if os.getenv("FAKE_API_DATA"):
            self.maas_client = None
            self.maas_state = FakeMaasState()
        else:
            self.maas_client, self.maas_state = connect_to_maas(creds)
        self.spinner = Spinner(15, 4)
        w = self.build_widgets()
        super().__init__(w)
        self.update()

    def build_widgets(self):
        self.message = Text("Please review available machines in MAAS",
                            align='center')
        self.status_pile = Pile([])
        self.button_grid = GridFlow([], 22, 1, 1, 'center')

        self.main_pile = Pile([self.message, self.status_pile,
                               Divider(),
                               self.button_grid])
        return Filler(self.main_pile, valign='middle')

    def scroll_down(self):
        pass

    def scroll_up(self):
        pass

    def selectable(self):
        return True

    def get_status(self):
        " returns (global_ok, [ok, condition])"
        self.maas_state.invalidate_nodes_cache()
        machines = self.maas_state.machines(state=MaasMachineStatus.READY)
        powerable_machines = [m for m in machines if m.power_type is not None]
        n_powerable = len(powerable_machines)
        multinic_machines = [m for m in machines if len(m.macaddress_set) > 1]

        n_multidisks = 0
        for m in powerable_machines:
            if self.maas_client is None:
                # Fake API testing, just don't break:
                continue

            lshw_data = self.maas_client.node_details(m.instance_id)
            disk_info = LSHWParser(lshw_data).get_disks()
            if len(disk_info) > 1:
                n_multidisks += 1

        conditions = [(n_powerable >= 6,
                       "At least 6 machines enlisted with power "
                       "control (currently {})".format(n_powerable)),
                      (len(multinic_machines) >= 1,
                       "At least one with 2 nics available for OpenStack"
                       " (currently {})".format(len(multinic_machines))),
                      (n_multidisks >= 5,
                       "Five machines with multiple disks"
                       " (currently {})".format(n_multidisks))]
        global_ok = all([ok for ok, _ in conditions])
        return global_ok, conditions

    def update(self):
        msg = ("Before continuing, check to be ensure sufficient machines are "
               "enlisted into MAAS to deploy Landscape:")
        self.message = Text(self.spinner.next_frame() + ['\n', msg, '\n'],
                            align='center')
        self.main_pile.contents[0] = (self.message,
                                      self.main_pile.options())

        global_ok, statuses = self.get_status()
        status_map = {True: "\u2713 ", False: "\N{TETRAGRAM FOR FAILURE} "}
        contents = [(Text([('label', status_map[status]), condition],
                          align='center'),
                     self.status_pile.options())
                    for status, condition
                    in statuses]
        self.status_pile.contents = contents

        if not global_ok:
            b = AttrMap(SelectableIcon(" ( Can't Continue )"),
                        'disabled_button', 'disabled_button_focus')
        else:
            b = AttrMap(Button("Continue",
                               on_press=self.do_continue),
                        'button', 'button_focus')

        self.button_grid.contents = [(b, self.button_grid.options())]

    @utils.async
    def do_continue(self, *args, **kwargs):
        self.installer.do_install()


class Spinner:

    chars = ["\N{DOTTED CIRCLE} ",
             "\N{WHITE CIRCLE} ",
             "\N{BLACK CIRCLE} ",
             "\N{BULLSEYE} ",
             "\N{FISHEYE} "]

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.cur = [random.randint(0, self.h)
                    for i in range(h)]
        self.vel = [random.randint(1, len(self.chars)-1)
                    for i in range(h)]

    def next_frame(self):
        r = []
        for j in range(self.h):
            r += [self.chars[(i - self.cur[j]) % len(self.chars)]
                  for i in range(self.w)]
            r.append("\n")
            self.cur[j] += self.vel[j]
        return r
