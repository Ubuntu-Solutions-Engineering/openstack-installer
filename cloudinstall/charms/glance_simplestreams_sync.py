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

from cloudinstall.charms import (CharmBase, DisplayPriorities)

log = logging.getLogger(__name__)


class CharmGlanceSimplestreamsSync(CharmBase):

    """ Charm directives for glance-simplestreams-sync  """

    charm_name = 'glance-simplestreams-sync'
    charm_rev = 3
    display_name = 'Glance - Simplestreams Image Sync'
    display_priority = DisplayPriorities.Other
    related = [('keystone:identity-service',
                'glance-simplestreams-sync:identity-service')]
    is_core = True
    available_sources = ['charmstore', 'next']


__charm_class__ = CharmGlanceSimplestreamsSync
