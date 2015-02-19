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
from cloudinstall.charms import (CharmBase, get_charm_config,
                                 DisplayPriorities)

log = logging.getLogger('cloudinstall.charms.compute')


class CharmSwift(CharmBase):

    """ swift directives """

    charm_name = 'swift-storage'
    charm_rev = 13
    display_name = 'Swift'
    menuable = True
    display_priority = DisplayPriorities.Storage
    related = ['swift-proxy']
    deploy_priority = 5
    default_replicas = 3
    isolate = True
    allow_multi_units = True

    @classmethod
    def required_num_units(self):
        charm_config, _ = get_charm_config()
        if 'swift-proxy' in charm_config:
            num_replicas = charm_config.get('replicas',
                                            self.default_replicas)
        else:
            num_replicas = self.default_replicas
        return num_replicas

    def post_proc(self):
        self.juju.set_config('glance-simplestreams-sync',
                             {'use_swift': 'True'})

__charm_class__ = CharmSwift
