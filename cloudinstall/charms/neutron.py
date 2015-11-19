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

log = logging.getLogger('cloudinstall.charms.neutron')


class CharmNeutron(CharmBase):

    """ neutron directives """

    charm_name = 'neutron-gateway'
    charm_rev = 7
    display_name = 'Neutron'
    deploy_priority = 99
    related = [('mysql:shared-db', 'neutron-gateway:shared-db'),
               ('nova-cloud-controller:quantum-network-service',
                'neutron-gateway:quantum-network-service'),
               ('ntp:juju-info', 'neutron-gateway:juju-info'),
               ('rabbitmq-server:amqp', 'neutron-gateway:amqp')]
    isolate = True
    constraints = {'mem': 2048,
                   'root-disk': 20480}
    allowed_assignment_types = [AssignmentType.BareMetal,
                                AssignmentType.KVM]
    is_core = True
    available_sources = ['charmstore', 'next']

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
            src=os.path.join(self.config.tmpl_path, "neutron-network.sh"),
            dst="/tmp/neutron-network.sh",
            juju_home=self.config.juju_home(use_expansion=True))
        utils.remote_run(
            unit.machine_id,
            cmds="sudo chmod +x /tmp/neutron-network.sh",
            juju_home=self.config.juju_home(use_expansion=True))
        utils.remote_run(
            unit.machine_id,
            cmds="sudo /tmp/neutron-network.sh {}".format(
                self.config.getopt('install_type')),
            juju_home=self.config.juju_home(use_expansion=True))

        session_id = self.config.getopt('session_id')
        if self.config.is_single():
            utils.pollinate(session_id, 'DS')
        elif self.config.is_multi():
            utils.pollinate(session_id, 'DM')

        self.ui.status_info_message("Done.")
        return False


__charm_class__ = CharmNeutron
