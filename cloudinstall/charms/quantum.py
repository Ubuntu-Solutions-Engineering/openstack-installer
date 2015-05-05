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

import os
import logging
from cloudinstall import utils
from cloudinstall.charms import CharmBase
from cloudinstall.placement.controller import AssignmentType

log = logging.getLogger('cloudinstall.charms.quantum')


class CharmQuantum(CharmBase):

    """ quantum directives """

    charm_name = 'quantum-gateway'
    charm_rev = 16
    # TODO: Charms are still called quantum, we want to display
    # them as Neutron
    display_name = 'Neutron'
    deploy_priority = 99
    related = [('mysql:shared-db', 'quantum-gateway:shared-db'),
               ('nova-cloud-controller:quantum-network-service',
                'quantum-gateway:quantum-network-service'),
               ('ntp:juju-info', 'quantum-gateway:juju-info'),
               ('rabbitmq-server:amqp', 'quantum-gateway:amqp')]
    isolate = True
    constraints = {'mem': 2048,
                   'root-disk': 20480}
    allowed_assignment_types = [AssignmentType.BareMetal,
                                AssignmentType.KVM]
    is_core = True

    def post_proc(self):
        """ performs additional network configuration for charm """
        svc = self.juju_state.service(self.charm_name)
        unit = svc.unit(self.charm_name)

        if unit.machine_id == '-1':
            return True

        self.ui.status_info_message("Validating network parameters "
                                    "for Neutron")
        utils.remote_cp(
            unit.machine_id,
            src=os.path.join(self.config.tmpl_path, "quantum-network.sh"),
            dst="/tmp/quantum-network.sh",
            juju_home=self.config.juju_home(use_expansion=True))
        utils.remote_run(
            unit.machine_id,
            cmds="sudo chmod +x /tmp/quantum-network.sh",
            juju_home=self.config.juju_home(use_expansion=True))
        utils.remote_run(
            unit.machine_id,
            cmds="sudo /tmp/quantum-network.sh {}".format(
                self.config.getopt('install_type')),
            juju_home=self.config.juju_home(use_expansion=True))
        return False


__charm_class__ = CharmQuantum
