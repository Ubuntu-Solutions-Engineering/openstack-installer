#
# state.py - MAAS instance state
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This package is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import json

class MaasState:
    DECLARED = 0
    COMMISSIONING = 1
    FAILED_TESTS = 2
    MISSING = 3
    READY = 4
    RESERVED = 5
    ALLOCATED = 6
    RETIRED = 7
    def __init__(self, raw_json):
        self._json = json.load(raw_json)

    def __iter__(self):
        return iter(self._json)

    def hostname_for_instance_id(self, id):
        for machine in self:
            if machine['resource_uri'] == id:
                return machine['hostname']

    @property
    def machines(self):
        return len(self._json)

    def num_in_state(self, state):
        return len(list(filter(lambda m: int(m["status"]) == state, self._json)))




