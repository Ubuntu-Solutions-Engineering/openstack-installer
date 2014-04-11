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

from collections import defaultdict
from cloudinstall.machine import Machine
from cloudinstall.log import logger

log = logger.getLogger(__name__)

class JujuState:
    """ Represents a global Juju state """

    def __init__(self, raw_yaml):
        """ Builds a JujuState from a file-like object containing the raw
        output from __juju status__

        :param raw_yaml: YAML object
        """
        self._yaml = yaml.load(raw_yaml)

    def machine(self, instance_id):
        """ Return single machine state

        :param str instance_id: machine instance_id
        :returns: machine
        :rtype: cloudinstall.machine.Machine()
        """
        for m in self.machines:
            if m.instance_id == instance_id:
                return m
        return Machine(-1, {'agent-state': 'unallocated',
                            'dns-name': 'unallocated'})

    def machines(self):
        """ Machines property

        :returns: machines known to juju
        :rtype: generator
        """
        for machine_id, machine in self._yaml['machines'].items():
            if '0' in machine_id:
                continue
            machine_units = {}
            for name in self.services:
                for k,v in self.units(name):
                    if machine_id in v.get('machine', '-1'):
                        machine_units[k] = v
            # Add units for machine
            machine['units'] = machine_units
            yield Machine(machine_id, machine)

    def machines_allocated(self):
        """ Machines allocated property

        :returns: Machines in an allocated state
        :rtype: generator
        """
        for m in self.machines():
            if m.agent_state in ['started', 'pending', 'down'] and \
               not m.is_machine_0:
                yield m

    def machines_unallocated(self):
        """ Machines unallocated property

        :returns: Machines in an unallocated state
        :rtype: list
        """
        for m in self.machines():
            if not m.agent_state or \
               'unallocated' in m.agent_state or \
                  m.agent_state not in ['started', 'pending', 'down']:
                yield m

    def units(self, name):
        """ Juju units property

        :param str name: service/charm name
        :returns: units for service
        :rtype: dict_items
        """
        return self.service(name).get('units', {}).items()

    def service(self, name):
        """ Return a single service entry

        :param str name: service/charm name
        :returns: a service entry
        :rtype: dict
        """
        return self.services.get(name, {})

    @property
    def services(self):
        """ Juju services property

        :returns: all loaded services
        :rtype: dict
        """
        return self._yaml.get('services', {})

    def _build_unit_map(self, compute_id, allow_id):
        """ Return a map of compute_id(unit): ([charm name], [unit name]),
        useful for defining maps between properties of units and what is
        deployed to them. """
        charms = defaultdict(lambda: ([], []))
        for name, service in self._yaml.get('services', {}).items():
            for unit_name, unit in service.get('units', {}).items():
                if 'machine' not in unit or not allow_id(str(unit['machine'])):
                    continue
                cs, us = charms[compute_id(unit)]
                cs.append(name)
                us.append(unit_name)
        return charms

    @property
    def assignments(self):
        """ Return a map of instance-ids and its charm/unit names,
        useful for figuring out what is deployed where. Note that
        these are physical machines, and containers are not included.

        :returns: [{instance-id: ([charm name], [unit name])}]
        :rtype: list
        """
        def by_instance_id(unit):
            return self._yaml['machines'][unit['machine']]['instance-id']

        def not_lxc(id_):
            return 'lxc' not in id_
        return self._build_unit_map(by_instance_id, not_lxc)

