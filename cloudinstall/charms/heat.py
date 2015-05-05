# Copyright 2015 James Beedy jamesbeedy@gmail.com
# Copyright 2015 Canonical, Ltd.
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


class CharmHeat(CharmBase):

    """ Openstack Heat directives """

    charm_name = 'heat'
    charm_rev = 7
    display_name = 'Heat'
    related = [('keystone:identity-service',
                'heat:identity-service'),
               ('mysql:shared-db',
                'heat:shared-db'),
               ('rabbitmq-server:amqp',
                'heat:amqp')]
    contrib = True

__charm_class__ = CharmHeat
