#
# cepy.py - Ceph instructions
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

from cloudinstall.charms import CharmBase


class CharmCeph(CharmBase):
    """ Ceph directives """

    charm_name = 'ceph'
    display_name = 'Ceph'

    def has_quorum(self):
        return len(list(self.state[2].machines_allocated())) >= 3

    def setup(self):
        """ Custom setup for ceph """
        if self.is_multi and self.has_quorum():
            self.client.deploy(self.charm_name, dict(instances=3))

__charm_class__ = CharmCeph
