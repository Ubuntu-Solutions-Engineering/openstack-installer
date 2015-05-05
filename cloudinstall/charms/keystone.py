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
import yaml
from cloudinstall.charms import CharmBase
from cloudinstall.utils import slurp

log = logging.getLogger('cloudinstall.charms.keystone')


class CharmKeystone(CharmBase):

    """ Openstack Keystone directives """

    charm_name = 'keystone'
    charm_rev = 25
    display_name = 'Keystone'
    related = [('mysql:shared-db', 'keystone:shared-db')]
    deploy_priority = 1
    is_core = True

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
        if self._is_auth_url_valid():
            return False

        service = self.juju_state.service('keystone')
        if len(service.units) < 1:
            return True

        unit = service.units[0]
        self.config.update_environments_yaml(
            key='auth-url',
            val='http://{0}:5000/v2.0/'.format(unit.public_address),
            provider='openstack'
        )
        log.debug("Updated keystone auth-url in openstack provider.")
        return False

__charm_class__ = CharmKeystone
