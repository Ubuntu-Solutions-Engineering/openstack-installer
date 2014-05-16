#
# __init__.py - MAAS instance state
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

from cloudinstall.machine import Machine


class MaasMachine(Machine):
    """ Single maas machine """

    @property
    def hostname(self):
        """ Query hostname reported by MaaS

        :returns: hostname
        :rtype: str
        """
        return self.machine.get('hostname', '')

    @property
    def status(self):
        """ Status of machine state

        Those statuses are defined as follows:
        DECLARED = 0
        COMMISSIONING = 1
        FAILED_TESTS = 2
        MISSING = 3
        READY = 4
        RESERVED = 5
        ALLOCATED = 6
        RETIRED = 7

        :returns: status
        :rtype: int
        """
        return self.machine.get('status', 0)

    @property
    def zone(self):
        """ Zone information

        :returns: zone information
        :rtype: dict
        """
        return self.machine.get('zone', {})

    @property
    def cpu_cores(self):
        """ Returns number of cpu-cores

        :returns: number of cpus
        :rtype: str
        """
        return self.machine.get('cpu_count', '0')

    @property
    def storage(self):
        """ Return storage

        :returns: storage size
        :rtype: str
        """
        try:
            _storage_in_gb = int(self.machine.get('storage')) / 1024
        except ValueError:
            return "N/A"
        return "{size}G".format(size=str(_storage_in_gb))

    @property
    def arch(self):
        """ Return architecture

        :returns: architecture type
        :rtype: str
        """
        return self.machine.get('architecture')

    @property
    def mem(self):
        """ Return memory

        :returns: memory size
        :rtype: str
        """
        try:
            _mem = int(self.machine.get('memory'))
        except ValueError:
            return "N/A"
        if _mem > 1024:
            _mem = _mem / 1024
            return "{size}G".format(size=str(_mem))
        else:
            return "{size}M".format(size=str(_mem))

    @property
    def power_type(self):
        """ Machine power type

        :returns: machines power type
        :rtype: str
        """
        return self.machine.get('power_type', 'None')

    @property
    def instance_id(self):
        """ Returns instance-id of a machine

        :returns: instance-id of machine
        :rtype: str
        """
        return self.machine.get('resource_uri', '')

    @property
    def system_id(self):
        """ Returns system id of a maas machine

        :returns: system id of machine
        :rtype: str
        """
        return self.machine.get('system_id', '')

    @property
    def ip_addresses(self):
        """ Ip addresses for machine

        :returns: ip addresses
        :rtype: list
        """
        return self.machine.get('ip_addresses', [])

    @property
    def mac_address(self):
        """ Macaddress set of maas machine

        :returns: mac_address and resource_uri
        :rtype: dict
        """
        return self.machine.get('macaddress_set', {})

    @property
    def tag_names(self):
        """ Tag names for machine

        :returns: tags associated with machine
        :rtype: list
        """
        return self.machine.get('tag_names', [])

    @property
    def tag(self):
        """ Machine tag

        :returns: tag defined
        :rtype: str
        """
        return self.machine.get('tag', '')

    @property
    def owner(self):
        """ Machine owner

        :returns: owner
        :rtype: str
        """
        return self.machine.get('owner', 'root')

    def __repr__(self):
        return "<MaasMachine({dns_name},{state},{mem}," \
            "{storage},{cpus})>".format(dns_name=self.hostname,
                                        state=self.agent_state,
                                        mem=self.mem,
                                        storage=self.storage,
                                        cpus=self.cpu_cores)


class MaasState:
    """ Represents global MaaS state """

    DECLARED = 0
    COMMISSIONING = 1
    FAILED_TESTS = 2
    MISSING = 3
    READY = 4
    RESERVED = 5
    ALLOCATED = 6
    RETIRED = 7

    def __init__(self, maas):
        self.maas = maas

    def __iter__(self):
        return iter(self.maas)

    def machine(self, instance_id):
        """ Return single machine state

        :param str instance_id: machine instance_id
        :returns: machine
        :rtype: cloudinstall.maas.MaasMachine
        """
        for m in self.machines():
            if m.instance_id == instance_id:
                return m
        return None

    def machines(self):
        """ Maas Machines

        :returns: machines known to maas
        :rtype: generator
        """
        for machine in self.maas:
            if 'juju-bootstrap.maas' in machine['hostname']:
                continue
            yield MaasMachine(-1, machine)

    def machines_allocated(self):
        """ Maas machines in an allocated(ready) state

        :returns: all machines in an allocated(ready) state
        :rtype: iter:
        """
        return [m for m in self.machines()
                if m.status == self.READY]

    def num_in_state(self, state):
        """ Number of machines in a particular state

        :param str state: a machine state
        :returns: number of machines in `status`
        :rtype: int
        """
        return len(list(filter(lambda m: int(m.status) == state,
                               self.machines())))
