#
# swift.py - Swift instructions
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

from cloudinstall.charms import CharmBase, CHARM_CONFIG, CHARM_CONFIG_FILENAME


class CharmSwift(CharmBase):
    """ swift directives """

    charm_name = 'swift-storage'
    display_name = 'Swift'
    related = ['swift-proxy']
    deploy_priority = 5
    default_replicas = 3
    isolate = True
    optional = True
    allow_multi_units = True

    def setup(self):
        """Custom setup for swift-storage to get replicas from config"""
        if 'swift-proxy' in CHARM_CONFIG:
            num_replicas = CHARM_CONFIG.get('replicas',
                                            self.default_replicas)
        else:
            num_replicas = self.default_replicas

        kwds = dict(instances=num_replicas)

        if self.charm_name in CHARM_CONFIG:
            kwds['configfile'] = CHARM_CONFIG_FILENAME

        self.client.deploy(self.charm_name, kwds)

__charm_class__ = CharmSwift
