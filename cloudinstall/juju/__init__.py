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


class JujuMachine:
    """ Represents a single machine state """

    def __init__(self, machine_id, machine):
        self.machine_id = machine_id
        self.machine = machine

    @property
    def is_machine_0(self):
        """ Checks if machine is bootstrapped node

        :rtype: bool
        """
        return "0" in self.machine_id

    @property
    def cpu_cores(self):
        """ Return number of cpu-cores

        :returns: number of cpus
        :rtype: str
        """
        return self.hardware('cpu-cores')

    @property
    def arch(self):
        """ Return architecture

        :returns: architecture type
        :rtype: str
        """
        return self.hardware('arch')

    @property
    def storage(self):
        """ Return storage

        :returns: storage size
        :rtype: str
        """
        try:
            _storage_in_gb = int(self.hardware('root-disk')[:-1]) / 1024
        except ValueError:
            return "N/A"
        return "{size}G".format(size=str(_storage_in_gb))

    @property
    def mem(self):
        """ Return memory

        :returns: memory size
        :rtype: str
        """
        try:
            _mem = int(self.hardware('mem')[:-1])
        except ValueError:
            return "N/A"
        if _mem > 1024:
            _mem = _mem / 1024
            return "{size}G".format(size=str(_mem))
        else:
            return "{size}M".format(size=str(_mem))

    def hardware(self, spec):
        """ Get hardware information

        :param spec: a hardware specification
        :type spec: str
        :returns: hardware of spec
        :rtype: str
        """
        _machine = self.machine.get('hardware', None)
        if _machine:
            _hardware_list = _machine.split(' ')
            for item in _hardware_list:
                k, v = item.split('=')
                if k in spec:
                    return v
        return 'N/A'

    @property
    def instance_id(self):
        """ Returns instance-id of a machine

        :param machine_id: machine number
        :type machine_id: int
        :returns: instance-id of machine
        :rtype: str
        """
        return self.machine['instance-id']

    @property
    def dns_name(self):
        """ Returns dns-name

        :rtype: str
        """
        return self.machine.get('dns-name', '')

    @property
    def agent_state(self):
        """ Returns agent-state

        :rtype: str
        """
        return self.machine.get('agent-state', '')

    @property
    def charms(self):
        """ Returns charms for machine

        :rtype: str
        """
        def charm_name(charm):
            return charm.split("/")[0]

        _charm_list = []
        for k in self.machine.get('units', []):
            _charm_list.append(charm_name(k))
        return _charm_list

    @property
    def units(self):
        """ Return units for machine

        :rtype: list
        """
        return self.machine.get('units', [])

    @property
    def containers(self):
        """ Return containers for machine

        :rtype: list
        """
        return self.machine.get('containers', [])

    def container(self, container_id):
        """ Inspect a container

        :param container_id: lxc container id
        :type container_id: int
        :returns: Returns a dictionary of the container information for
                  specific machine and lxc id.
        :rtype: dict
        """
        lxc = "%s/lxc/%s" % (self.machine_id, container_id)
        return JujuMachine(lxc, self.containers.get(lxc, {}))


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

        :param instance_id: machine instance_id
        :type instance_id: str
        :returns: machine
        :rtype: .. py:class:: JujuMachine
        """
        for m in self.machines:
            if m.instance_id == instance_id:
                return m

    @property
    def machines(self):
        """ Machines property

        :returns: machines known to juju
        :rtype: list
        """
        results = []
        for machine_id, machine in self._yaml['machines'].items():
            machine_units = {}
            for name in self.services:
                for k,v in self.units(name):
                    if machine_id in v.get('machine', '-1'):
                        machine_units[k] = v
            # Add units for machine
            machine['units'] = machine_units
            results.append(JujuMachine(machine_id, machine))
        return results

    @property
    def machines_allocated(self):
        """ Machines allocated property

        :returns: Machines in an allocated state
        :rtype: list
        """
        allocated = []
        for m in self.machines:
            if m.agent_state in ['started', 'pending', 'down'] and \
               not '0' in m.machine_id:
                allocated.append(m)
        return allocated

    @property
    def machines_unallocated(self):
        """ Machines unallocated property

        :returns: Machines in an unallocated state
        :rtype: list
        """
        unallocated = []
        for m in self.machines:
            if m.agent_state not in ['started', 'pending', 'down']:
                unallocated.append(m)
        return unallocated

    def units(self, name):
        """ Juju units property

        :param name: service/charm name
        :type name: str
        :returns: units for service
        :rtype: dict_items
        """
        return self.service(name).get('units', {}).items()

    def service(self, name):
        """ Return a single service entry

        :param name: service/charm name
        :type name: str
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

