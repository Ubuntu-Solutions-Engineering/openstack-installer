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
from cloudinstall.placement.controller import AssignmentType

log = logging.getLogger('cloudinstall.charms.cinder')


class CharmCinder(CharmBase):

    """ Cinder directives """

    charm_name = 'cinder'
    charm_rev = 17
    display_name = 'Cinder'
    related = [('cinder:image-service', 'glance:image-service'),
               ('cinder:storage-backend',
                'cinder-ceph:storage-backend'),
               ('rabbitmq-server:amqp',
                'cinder:amqp'),
               ('cinder:identity-service',
                'keystone:identity-service'),
               ('nova-cloud-controller:cinder-volume-service',
                'cinder:cinder-volume-service'),
               ('cinder:shared-db', 'mysql:shared-db')]

    allowed_assignment_types = [AssignmentType.BareMetal,
                                AssignmentType.KVM]

__charm_class__ = CharmCinder
