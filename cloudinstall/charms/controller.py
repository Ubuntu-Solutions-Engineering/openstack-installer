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
from cloudinstall.netutils import is_ipv6
from cloudinstall.charms import CharmBase

log = logging.getLogger('cloudinstall.charms.controller')


class CharmNovaCloudController(CharmBase):

    """ Openstack Nova Cloud Controller directives """

    charm_name = 'nova-cloud-controller'
    charm_rev = 60
    display_name = 'Controller'
    deploy_priority = 2
    related = [('nova-cloud-controller:shared-db',
                'mysql:shared-db'),
               ('rabbitmq-server:amqp',
                'nova-cloud-controller:amqp'),
               ('glance:image-service',
                'nova-cloud-controller:image-service'),
               ('keystone:identity-service',
                'nova-cloud-controller:identity-service')]
    allow_multi_units = False
    is_core = True
    available_sources = ['charmstore', 'next']

    def post_proc(self):
        """ post processing for nova-cloud-controller """
        svc = self.juju_state.service(self.charm_name)
        unit = svc.unit(self.charm_name)
        k_svc = self.juju_state.service('keystone')
        keystone = k_svc.unit('keystone')
        openstack_password = self.config.getopt('openstack_password')
        public_address = keystone.public_address
        if is_ipv6(public_address):
            public_address = "[%s]".format(public_address)
            log.debug("Found ipv6 address, {}".format(public_address))

        if unit.machine_id == '-1':
            return True

        for u in ['admin', 'ubuntu']:
            env = self._openstack_env(u,
                                      openstack_password,
                                      u, public_address)
            self._openstack_env_save(u, env)
            utils.remote_cp(
                unit.machine_id,
                src=self._openstack_env_path(u),
                dst='/tmp/openstack-{u}-rc'.format(u=u),
                juju_home=self.config.juju_home(use_expansion=True))

        setup_script_path = self.render_setup_script()
        remote_setup_script_path = "/tmp/nova-controller-setup.sh"
        utils.remote_cp(
            unit.machine_id,
            src=setup_script_path,
            dst=remote_setup_script_path,
            juju_home=self.config.juju_home(use_expansion=True))
        utils.remote_run(
            unit.machine_id,
            cmds="chmod +x {}".format(remote_setup_script_path),
            juju_home=self.config.juju_home(use_expansion=True))
        utils.remote_cp(
            unit.machine_id,
            src=utils.ssh_pubkey(),
            dst="/tmp/id_rsa.pub",
            juju_home=self.config.juju_home(use_expansion=True))
        err = utils.remote_run(
            unit.machine_id,
            cmds="/tmp/nova-controller-setup.sh "
            "\"{p}\" \"{install_type}\"".format(
                p=openstack_password,
                install_type=self.config.getopt('install_type')),
            juju_home=self.config.juju_home(use_expansion=True))
        if err['status'] != 0:
            # something happened during nova setup, re-run
            return True
        return False

    def render_setup_script(self):
        setup_template = utils.load_template("nova-controller-setup.sh")
        if self.config.is_single():
            lxc_network = self.config.getopt('lxc_network')
            N = lxc_network.split('.')[2]
        else:
            # N is used to define networks for single, so we simply
            # set a dummy value for multi
            N = 0

        setup_script_path = os.path.join(self.config.cfg_path,
                                         "nova-controller-setup.sh")
        osrel = self.config.getopt('openstack_release')
        template_args = dict(N=N,
                             openstack_release=osrel)
        utils.spew(setup_script_path,
                   setup_template.render(template_args))
        return setup_script_path


__charm_class__ = CharmNovaCloudController
