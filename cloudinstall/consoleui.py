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

""" ConsoleUI - headless interface to Installer """

from __future__ import unicode_literals
import logging

from cloudinstall.task import TaskerConsole

log = logging.getLogger('cloudinstall.consoleui')


class ConsoleUI:

    def __init__(self):
        self._missing_attrs = []

    def tasker(self, loop, config):
        """ Return console tasker """
        return TaskerConsole(self, loop, config)

    def status_info_message(self, msg):
        log.info(msg)

    def show_step_info(self, msg):
        log.info(msg)

    def __getattr__(self, attr):
        """
        Override attribute lookup since ConsoleUI doesn't implement
        everything PegagusUI does.
        """

        def nofunc(*args, **kwargs):
            self._missing_attrs.append(attr)

        try:
            getattr(ConsoleUI, attr)
        except:
            # Log the invalid attribute call
            log.info("Missing ConsoleUI() attribute: {}".format(attr))
            setattr(self.__class__, attr, nofunc)
            return getattr(ConsoleUI, attr)

    def __repr__(self):
        return "<Ubuntu OpenStack Installer Console Interface>"
