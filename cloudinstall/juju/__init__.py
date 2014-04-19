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

import yaml
import itertools

from collections import defaultdict
from cloudinstall.machine import Machine
from cloudinstall.service import Service
from cloudinstall.log import log

log.name = 'cloudinstall.juju'

class JujuState:
    """ Represents a global Juju state """

    def __init__(self, raw_yaml):
        """ Builds a JujuState from a file-like object containing the raw
        output from __juju status__

        :param raw_yaml: YAML object
        """
        self._yaml = yaml.load(raw_yaml)
        self.valid_states = ['pending', 'started', 'down']

    def __validate_allocation(self, machine):
        """ Private function to test if machine is in an allocated
        state.
        """
        return machine.is_machine_1 and \
            (machine.is_cloud_controller or \
             machine.agent_state in self.valid_states)

    def __validate_unallocation(self, machine):
        """ Private function to test if machine is in an unallocated
        state.
        """
        return not machine.is_machine_1 and \
            not machine.is_compute

    def machine(self, instance_id):
        """ Return single machine state

        :param str instance_id: machine instance_id
        :returns: machine
        :rtype: cloudinstall.machine.Machine()
        """
        return next(filter(lambda x: x.instance_id == instance_id,
                           self.machines())) or Machine(-1, {})

    def machines(self):
        """ Machines property

        :returns: machines known to juju
        :rtype: generator
        """
        for machine_id, machine in self._yaml['machines'].items():
            if '0' in machine_id:
                continue

            # Add units for machine
            machine['units'] = []
            for svc in self.services:
                for unit in svc.units:
                    if machine_id == unit.machine_id:
                        machine['units'].append(unit)
            yield Machine(machine_id, machine)

    def machines_allocated(self):
        """ Machines allocated property

        :returns: Machines in an allocated state
        :rtype: iter
        """
        return filter(self.__validate_allocation,
                      self.machines())

    def machines_unallocated(self):
        """ Machines unallocated property

        :returns: Machines in an unallocated state
        :rtype: iter
        """
        return filter(self.__validate_unallocation,
                      self.machines())

    def service(self, name):
        """ Return a single service entry

        :param str name: service/charm name
        :returns: a service entry or None
        :rtype: Service()
        """
        try:
            return next(filter(lambda s: s.service_name == name,
                               self.services))
        except StopIteration:
            return None

    @property
    def services(self):
        """ Juju services property

        :returns: Service() of all loaded services
        :rtype: generator
        """
        for name, service in self._yaml.get('services', {}).items():
            yield Service(name, service)
