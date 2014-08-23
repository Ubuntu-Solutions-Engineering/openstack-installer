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
    # TODO: Charms are still called quantum, we want to display
    # them as Neutron
    display_name = 'Neutron'
    related = ['mysql', 'nova-cloud-controller', 'rabbitmq-server']
    isolate = True
    optional = False
    menuable = True
    constraints = {'mem': 2048,
                   'root-disk': 20480}

    def post_proc(self):
        """ performs additional network configuration for charm """
        if not self.wait_for_agent():
            return True
        svc = self.juju_state.service(self.charm_name)
        unit = svc.unit(self.charm_name)

        if unit.machine_id == '-1':
            return True

        self.ui.status_info_message("Updating network parameters "
                                    "for Neutron")
        utils.remote_cp(
            unit.machine_id,
            src=os.path.join(self.config.tmpl_path, "quantum-network.sh"),
            dst="/tmp/quantum-network.sh")
        utils.remote_run(unit.machine_id,
                         cmds="sudo chmod +x /tmp/quantum-network.sh")
        utils.remote_run(unit.machine_id,
                         cmds="sudo /tmp/quantum-network.sh")
        return False


__charm_class__ = CharmQuantum
