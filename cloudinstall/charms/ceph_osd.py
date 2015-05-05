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

log = logging.getLogger('cloudinstall.charms.ceph')


class CharmCephOSD(CharmBase):

    """ Ceph OSD directives """

    charm_name = 'ceph-osd'
    charm_rev = 10
    display_name = 'Ceph OSD'
    allow_multi_units = True
    related = [('ceph:osd', 'ceph-osd:mon'),
               ('ntp:juju-info', 'ceph-osd:juju-info')]
    depends = ['ntp', 'ceph']
    isolate = True

__charm_class__ = CharmCephOSD
