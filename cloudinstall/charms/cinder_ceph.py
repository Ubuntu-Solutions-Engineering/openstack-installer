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

log = logging.getLogger('cloudinstall.charms.cinder_ceph')


class CharmCinderCeph(CharmBase):

    """ Cinder-Ceph directives """

    charm_name = 'cinder-ceph'
    charm_rev = 7
    display_name = 'Cinder-Ceph'
    deploy_priority = 5
    subordinate = True
    depends = ['ceph', 'cinder']

__charm_class__ = CharmCinderCeph
