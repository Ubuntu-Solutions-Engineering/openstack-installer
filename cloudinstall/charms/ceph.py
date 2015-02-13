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

from cloudinstall.charms import CharmBase, DisplayPriorities

log = logging.getLogger('cloudinstall.charms.ceph')


class CharmCeph(CharmBase):

    """ Ceph directives """

    charm_name = 'ceph'
    charm_rev = 31
    display_name = 'Ceph'
    menuable = True
    display_priority = DisplayPriorities.Storage
    related = ['glance', 'nova-compute']
    deploy_priority = 5
    disabled = False
    isolate = True
    allow_multi_units = True
    constraints = {'mem': 1024,
                   'root-disk': 20480}

    @classmethod
    def required_num_units(self):
        return 3


__charm_class__ = CharmCeph
