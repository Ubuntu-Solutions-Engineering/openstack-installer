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

""" Simple observer class
"""

import logging

log = logging.getLogger('cloudinstall.notify')


class Observer:
    _observers = []

    def __init__(self):
        self._observers.append(self)
        self._observables = {}

    def observe(self, event_name, cb):
        self._observables[event_name] = cb


class Event:
    def __init__(self, name, autoemit=True):
        self.name = name
        if autoemit:
            self.emit()

    def emit(self):
        for observer in Observer._observers:
            if self.name in observer._observables:
                log.debug("Event called: {}".format(
                    observer._observables[self.name]))
                ret = observer._observables[self.name]()
                log.debug("Processed event: {}".format(ret))
