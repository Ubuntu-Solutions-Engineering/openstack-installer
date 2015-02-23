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

log = logging.getLogger('cloudinstall.charms.ntp')


class CharmNtp(CharmBase):

    """ NTP directives """

    charm_name = 'ntp'
    charm_rev = 6
    display_name = 'NTP'
    related = {'nova-compute': ('ntp:juju-info',
                                'nova-compute:juju-info'),
               'neutron-gateway': ('ntp:juju-info',
                                   'quantum-gateway:juju-info'),
               'ceph-osd': ('ntp:juju-info', 'ceph-osd:juju-info')}
    subordinate = True

    def set_relations(self):
        if not self.wait_for_agent([self.charm_name, 'nova-compute',
                                    'quantum-gateway']):
            return True
        for charm in self.related.keys():
            try:
                rv = self.juju.add_relation(*self.related[charm])
                log.debug("add_relation {} "
                          "returned {}".format(charm, rv))
            except:
                log.exception("{} not ready for relation".format(charm))
                return True

__charm_class__ = CharmNtp
