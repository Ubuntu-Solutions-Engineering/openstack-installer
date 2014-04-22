#
# keystone.py - Keystone Charm instructions
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

from os.path import expanduser
from cloudinstall.charms import CharmBase


class CharmKeystone(CharmBase):
    """ Openstack Keystone directives """

    charm_name = 'keystone'

    def __openstack_password(self):
        PASSWORD_FILE = expanduser('~/.cloud-install/openstack.passwd')
        try:
            with open(PASSWORD_FILE) as f:
                OPENSTACK_PASSWORD = f.read().strip()
        except IOError:
            OPENSTACK_PASSWORD = 'password'
        return OPENSTACK_PASSWORD

    def setup(self):
        super(CharmKeystone, self).setup()
        self.client.set_config(self.charm_name,
                               {'admin-password': self.__openstack_password()})

    def set_relations(self):
        self.client.add_relation(self.charm_name,
                                 'mysql')


