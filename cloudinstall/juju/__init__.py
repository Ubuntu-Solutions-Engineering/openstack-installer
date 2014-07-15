#
# __init__.py - Juju state
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

""" Represents a juju status """

import logging

from cloudinstall.config import Config
from cloudinstall.machine import Machine
from cloudinstall.service import Service

log = logging.getLogger('cloudinstall.juju')


class JujuState:
    """ Represents a global Juju state """

    def __init__(self, juju):
        """ Builds a JujuState

        :param juju: Juju API connection
        """
        self.config = Config()
        self.juju = juju
        self.valid_states = ['pending', 'started', 'down']

    def machine(self, machine_id):
        """ Return single machine state

        :param str machine_id: machine machine_id
        :returns: machine
        :rtype: cloudinstall.machine.Machine()
        """
        r = next(filter(lambda x: x.machine_id == machine_id,
                 self.machines()), Machine(-1, {}))
        return r

    def machines(self):
        """ Machines property

        :returns: machines known to juju (except bootstrap)
        :rtype: generator
        """
        for machine_id, machine in self.juju.status()['Machines'].items():
            if '0' == machine_id:
                continue
            yield Machine(machine_id, machine)

    def machines_allocated(self):
        """ Machines allocated property

        :returns: all machines in an allocated state (see self.valid_states)
        :rtype: iter
        """
        return [m for m in self.machines()
                if m.agent_state in self.valid_states or
                m.agent['Status'] in self.valid_states]

    def service(self, name):
        """ Return a single service entry

        :param str name: service/charm name
        :returns: a service entry or None
        :rtype: Service()
        """
        r = next(filter(lambda s: s.service_name == name,
                        self.services), Service(name, {}))
        return r

    @property
    def services(self):
        """ Juju services property

        :returns: Service() of all loaded services
        :rtype: generator
        """
        for name, service in self.juju.status()['Services'].items():
            yield Service(name, service)

    @property
    def networks(self):
        """ Juju netwoks property
        """
        return self.juju.status()['Networks']
