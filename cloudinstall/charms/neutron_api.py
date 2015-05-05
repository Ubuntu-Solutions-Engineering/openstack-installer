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

from cloudinstall.charms import CharmBase

log = logging.getLogger('cloudinstall.charms.neutron_api')


class CharmNeutronAPI(CharmBase):

    charm_name = 'neutron-api'
    charm_rev = 14
    display_name = 'Neutron API'
    openstack_release_min = 'j'
    related = [('neutron-api:identity-service',
                'keystone:identity-service'),
               ('neutron-openvswitch:neutron-plugin-api',
                'neutron-api:neutron-plugin-api'),
               ('mysql:shared-db', 'neutron-api:shared-db'),
               ('rabbitmq-server:amqp',
                'neutron-api:amqp'),
               ('quantum-gateway:neutron-plugin-api',
                'neutron-api:neutron-plugin-api'),
               ('nova-cloud-controller:neutron-api',
                'neutron-api:neutron-api')]
    is_core = True


__charm_class__ = CharmNeutronAPI
