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

from cloudinstall.charms import CharmBase


class CharmGlance(CharmBase):

    """ Openstack Glance directives """

    charm_name = 'glance'
    charm_rev = 19
    display_name = 'Glance'
    related = [('mysql:shared-db', 'glance:shared-db'),
               ('keystone:identity-service', 'glance:identity-service'),
               ('rabbitmq-server:amqp', 'glance:amqp')]
    is_core = True

__charm_class__ = CharmGlance
