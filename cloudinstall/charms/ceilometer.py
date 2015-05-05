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

import logging
from cloudinstall.charms import CharmBase

log = logging.getLogger('cloudinstall.charms.ceilometer')


class CharmCeilometer(CharmBase):

    """ Ceilometer directives """

    charm_name = 'ceilometer'
    charm_rev = 9
    display_name = 'Ceilometer'
    deploy_priority = 100
    contrib = True
    related = [('ceilometer:shared-db', 'mongodb:database'),
               ('ceilometer:identity-service',
                'keystone:identity-service'),
               ('ceilometer:amqp', 'rabbitmq-server:amqp'),
               ('ceilometer:identity-notifications',
                'keystone:identity-notifications'),
               ('ceilometer:ceilometer-service',
                'ceilometer-agent:ceilometer-service')]
    depends = ['ceilometer-agent', 'mongodb']

__charm_class__ = CharmCeilometer
