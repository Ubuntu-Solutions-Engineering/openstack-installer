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

import os
import logging
from cloudinstall import utils
from cloudinstall.charms import CharmBase

log = logging.getLogger('cloudinstall.charms.quantum')


class CharmQuantum(CharmBase):
    """ quantum directives """

    charm_name = 'quantum-gateway'
    display_name = 'Quantum'
    related = ['mysql', 'nova-cloud-controller', 'rabbitmq-server']
    isolate = True
    optional = False
    constraints = {'mem': '1G',
                   'root-disk': '2G'}

    def post_proc(self):
        """ performs additional network configuration for charm """
        unit = self.wait_for_agent()
        if unit:
            utils.remote_cp(
                unit.machine_id,
                src=os.path.join(self.tmpl_path, "quantum-network.sh"),
                dst="/tmp/quantum-network.sh")
            utils.remote_run(unit.machine_id,
                             cmds="sudo chmod +x /tmp/quantum-network.sh")
            utils.remote_run(unit.machine_id,
                             cmds="sudo /tmp/quantum-network.sh")
            return False
        return True


__charm_class__ = CharmQuantum
