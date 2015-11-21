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

import logging
import os
import random
from urwid import (AttrMap, Button, Divider, Filler, Padding, Pile,
                   SelectableIcon, Text, WidgetWrap)

from cloudinstall.maas import connect_to_maas, FakeMaasState, MaasMachineStatus
from cloudinstall import async

log = logging.getLogger('cloudinstall.machinewait')


class MachineWaitView(WidgetWrap):

    def __init__(self, display_controller, installer, config):
        self.display_controller = display_controller
        self.installer = installer
        self.config = config
        creds = self.config.getopt('maascreds')
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

        self.button_pile = Pile([])

        self.main_pile = Pile([self.message,
                               Divider(),
                               self.button_pile])
        return Filler(self.main_pile, valign='middle')

    def keypress(self, size, key):
        key = {'tab': 'down', 'shift tab': 'up'}.get(key, key)
        return super().keypress(size, key)

    def scroll_down(self):
        pass

    def scroll_up(self):
        pass

    def selectable(self):
        return True

    def get_status(self):
        " returns (global_ok, [ok, condition])"
        self.maas_state.invalidate_nodes_cache()
        cons = self.config.getopt('constraints')
        machines = self.maas_state.machines(state=MaasMachineStatus.READY,
                                            constraints=cons)
        powerable_machines = [m for m in machines if m.power_type is not None]
        n_powerable = len(powerable_machines)

        conditions = [(n_powerable >= 1,
                       "At least one machine enlisted with power "
                       "control (currently {})".format(n_powerable))]

        global_ok = all([ok for ok, _ in conditions])
        return global_ok, conditions

    def update(self):
        msg = ("Before continuing, ensure that at least one machine is "
               "enlisted into MAAS:")
        self.message = Text(self.spinner.next_frame() + ['\n', msg, '\n'],
                            align='center')
        contents = [(self.message,
                     self.main_pile.options())]

        global_ok, statuses = self.get_status()
        status_map = {True: ('success_icon', "\u2713 "),
                      False: ('error_icon', "<!> ")}
        contents += [(Text([status_map[status], condition],
                           align='center'),
                      self.main_pile.options())
                     for status, condition
                     in statuses]
        contents += [(Divider(), self.main_pile.options()),
                     (self.button_pile, self.main_pile.options())]
        self.main_pile.contents = contents

        if not global_ok:
            b = AttrMap(SelectableIcon(" ( Can't Continue ) "),
                        'disabled_button', 'disabled_button_focus')
        else:
            b = AttrMap(Button("Continue",
                               on_press=self.do_continue),
                        'button_primary', 'button_primary focus')

        cancel_b = AttrMap(Button("Cancel",
                                  on_press=self.do_cancel),
                           'button_secondary',
                           'button_secondary focus')
        self.button_pile.contents = [(Padding(cancel_b, width=24,
                                              align='center'),
                                      self.button_pile.options()),
                                     (Padding(b, width=24, align='center'),
                                      self.button_pile.options())]

        # ensure that the button is always focused:
        self.main_pile.focus_position = len(self.main_pile.contents) - 1

    def do_continue(self, *args, **kwargs):
        async.submit(self.installer.do_install,
                     self.display_controller.show_exception_message)

    def do_cancel(self, *args, **kwargs):
        raise SystemExit("Installation cancelled.")


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
        self.vel = [random.randint(1, len(self.chars) - 1)
                    for i in range(h)]

    def next_frame(self):
        r = []
        for j in range(self.h):
            r += [self.chars[(i - self.cur[j]) % len(self.chars)]
                  for i in range(self.w)]
            r.append("\n")
            self.cur[j] += self.vel[j]
        return r
