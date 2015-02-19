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
import yaml
from cloudinstall.charms import CharmBase
from cloudinstall.utils import slurp

log = logging.getLogger('cloudinstall.charms.keystone')


class CharmKeystone(CharmBase):

    """ Openstack Keystone directives """

    charm_name = 'keystone'
    charm_rev = 12
    display_name = 'Keystone'
    related = ['mysql']
    deploy_priority = 1
    menuable = True

    def deploy(self, m):
        mysql_exists = self.wait_for_agent(['mysql'])
        if not mysql_exists:
            log.debug("mysql not yet available, deferring keystone deploy")
            return True
        log.debug("mysql is available, deploying keystone")
        return super().deploy(m)

    def _is_auth_url_valid(self):
        existing_yaml = yaml.load(slurp(self.config.juju_environments_path))
        existing_yaml = existing_yaml['environments']
        if 'openstack' in existing_yaml:
            if 'http://keystoneurl' in existing_yaml['openstack']['auth-url']:
                return False
            else:
                log.debug("Found an existing keystone auth-url, skipping.")
                return True
        return False

    def post_proc(self):
        # Dont bother updating auth-url if its already set
        if self._is_auth_url_valid():
            return False

        keystone = self.wait_for_agent()
        if not keystone:
            return True
        service = self.juju_state.service('keystone')
        if len(service.units) > 0:
            unit = service.units[0]
        self.config.update_environments_yaml(
            key='auth-url',
            val='http://{0}:5000/v2.0/'.format(unit.public_address),
            provider='openstack'
        )
        log.debug("Updated keystone auth-url in openstack provider.")
        return False

__charm_class__ = CharmKeystone
