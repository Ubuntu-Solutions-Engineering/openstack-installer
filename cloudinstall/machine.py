#
# machine.py - Machine
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

import logging
from cloudinstall.utils import human_to_mb

log = logging.getLogger('cloudinstall.machine')


def satisfies(machine, constraints):
    """Evaluates whether a machine's hardware matches constraints.

    returns tuple of (bool, list-of-failed constraint keys)

    success will be (True, [])

    If constraints is None or an empty dict, then any machine will be
    evaluated as satisfying the constraints.

    Note that if a machine has '*' as a value, that value satisfies
    any constraint.

    """
    kmap = dict(mem='memory',
                arch='architecture',
                storage='storage',
                cpu_cores='cpu_count')
    kmap['root-disk'] = 'storage'

    cons_checks = []

    if constraints is None:
        return (True, [])

    for k, v in constraints.items():
        if k == 'arch':
            mval = machine.machine[kmap[k]]
            if mval != '*' and mval != v:
                cons_checks.append(k)
        else:
            mval = machine.machine[kmap[k]]

            if mval == '*':
                # '*' always satisfies.
                continue

            if not str(v).isdecimal():
                v = human_to_mb(v)

            if mval < v:
                cons_checks.append(k)

    rval = (len(cons_checks) == 0), cons_checks
    log.debug("returning {} for satisfies({},{})".format(
        rval, machine, constraints))
    return rval


class Machine:
    """ Base machine class """

    def __init__(self, machine_id, machine):
        self.machine_id = machine_id
        self.machine = machine
        self._cpu_cores = self.hardware('cpu-cores')
        self._storage = self.hardware('root-disk')
        self._mem = self.hardware('memory')
        self.agent = self.machine.get('Agent', None)
        self.agent_state = self.machine.get('AgentState', None)
        self.agent_state_info = self.machine.get('AgentStateInfo', None)
        self.agent_version = self.machine.get('AgentVersion', None)
        self.dns_name = self.machine.get('DNSName', '')
        self.err = self.machine.get('Err', None)
        self.has_vote = self.machine.get('HasVote')
        self.wants_vote = self.machine.get('WantsVote')

    @property
    def instance_id(self):
        """ Returns InstanceId

        :returns: instance ID
        :rtype: str
        """
        return self.machine.get('InstanceId', None)

    @property
    def cpu_cores(self):
        """ Return number of cpu-cores

        :returns: number of cpus
        :rtype: str
        """
        return self._cpu_cores

    @cpu_cores.setter
    def cpu_cores(self, val):
        self._cpu_cores = val

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
            self._storage = int(self._storage[:-1]) / 1024
            return "{size}G".format(size=str(self._storage))
        except:
            return "N/A"

    @storage.setter
    def storage(self, val):
        self._storage = val

    @property
    def mem(self):
        """ Return memory

        :returns: memory size
        :rtype: str
        """
        return "{size}".format(size=str(self._mem))

    @mem.setter
    def mem(self, val):
        self._mem = val

    def hardware(self, spec):
        """ Get hardware information

        :param spec: a hardware specification
        :type spec: str
        :returns: hardware of spec
        :rtype: str
        """
        _machine = self.machine.get('Hardware', None)
        if _machine:
            _hardware_list = _machine.split(' ')
            for item in _hardware_list:
                k, v = item.split('=')
                if k in spec:
                    return v
        return "N/A"

    @property
    def containers(self):
        """ Return containers for machine

        :rtype: generator
        """
        _containers = self.machine.get('Containers', {}).items()
        for container_id, container in _containers:
            yield Machine(container_id, container)

    def container(self, container_id):
        """ Inspect a container

        :param container_id: lxc container id
        :type container_id: int
        :returns: Returns a dictionary of the container information for
                  specific machine and lxc id.
        :rtype: dict
        """
        for m in self.containers:
            if m.machine_id == container_id:
                return m
        return Machine('0/lxc/0', {'agent-state': 'unallocated',
                                   'dns-name': 'unallocated'})

    def __str__(self):
        return ("id={machine_id} state={state}, "
                "dns-name={dns_name} mem={mem} "
                "storage={storage} "
                "cpus={cpus}".format(machine_id=self.machine_id,
                                     dns_name=self.dns_name,
                                     state=self.agent_state,
                                     mem=self.mem,
                                     storage=self.storage,
                                     cpus=self.cpu_cores))

    def __repr__(self):
        return ("<Machine({dns_name},{state},{mem},"
                "{storage},{cpus})>".format(dns_name=self.dns_name,
                                            state=self.agent_state,
                                            mem=self.mem,
                                            storage=self.storage,
                                            cpus=self.cpu_cores))
