#
# controller.py - Nova Cloud Controller Charm instructions
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

import os
import logging
from cloudinstall import utils
from cloudinstall.charms import CharmBase

log = logging.getLogger('cloudinstall.charms.controller')


class CharmNovaCloudController(CharmBase):
    """ Openstack Nova Cloud Controller directives """

    charm_name = 'nova-cloud-controller'
    display_name = 'Nova Cloud Controller'
    related = ['mysql', 'rabbitmq-server', 'glance', 'keystone']
    allow_multi_units = True

    def post_proc(self):
        """ post processing for nova-cloud-controller """
        unit = self.wait_for_agent()
        if unit:
            # We need to get keystone public_address for auth_url here
            keystone = self.wait_for_agent('keystone')
            if not keystone:
                return True
            for u in ['admin', 'ubuntu']:
                env = self._openstack_env(u, self.openstack_password(),
                                          u, keystone.public_address)
                self._openstack_env_save(u, env)
                utils.remote_cp(unit.machine_id,
                                src=self._openstack_env_path(u),
                                dst='/tmp/openstack-{u}-rc'.format(u=u))
            utils.remote_cp(
                unit.machine_id,
                src=os.path.join(self.tmpl_path,
                                 "nova-controller-setup.sh"),
                dst="/tmp/nova-controller-setup.sh")
            utils.remote_cp(
                unit.machine_id,
                src=self._pubkey(),
                dst="/tmp/id_rsa.pub")
            err = utils.remote_run(unit.machine_id,
                                   cmds="/tmp/nova-controller-setup.sh "
                                        "{p}".format(
                                            p=self.openstack_password()))
            if err['ret'] == 1:
                # something happened during nova setup, re-run
                return True
            return False
        return True


__charm_class__ = CharmNovaCloudController
