#
# ceph.py - Ceph instructions
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

import logging

from cloudinstall.charms import CharmBase

log = logging.getLogger('cloudinstall.charms.ceph')


class CharmCeph(CharmBase):
    """ Ceph directives """

    charm_name = 'ceph'
    display_name = 'Ceph'
    related = ['glance', 'mysql', 'rabbitmq-server']
    deploy_priority = 5
    default_instances = 3
    optional = True
    disabled = False
    allow_multi_units = True

    def has_quorum(self):
        return len(list(self.state[2].machines_allocated())) >= 3

    def setup(self):
        """ Custom setup for ceph """
        if not self.has_quorum():
            log.debug("Insufficient machines allocated - ceph can't deploy.")
            return
        if not self.is_multi:
            log.debug("Ceph not currently supported on single installs")
            return

        self.client.deploy(self.charm_name,
                           dict(instances=self.default_instances))

__charm_class__ = CharmCeph
