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
from collections import Counter
from enum import Enum, unique
import logging
import time


log = logging.getLogger('cloudinstall.maas')


@unique
class MaasMachineStatus(Enum):
    """Symbolic names for maas API status numbers.

    -1, UNKNOWN is never returned by maas API. It's used here to
    denote a MaasMachine object that wasn't created from a Maas API
    return.
    """
    UNKNOWN = -1
    DECLARED = 0
    COMMISSIONING = 1
    FAILED_TESTS = 2
    MISSING = 3
    READY = 4
    RESERVED = 5
    ALLOCATED = 6
    RETIRED = 7

    def __str__(self):
        return self.name.lower()


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

        :returns: status enum
        :rtype: MaasMachineStatus
        """
        return MaasMachineStatus(self.machine.get('status',
                                                  MaasMachineStatus.UNKNOWN))

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
        return "{size:.2f}G".format(size=_storage_in_gb)

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

    def __str__(self):
        return repr(self)

    def filter_label(self):
        d = dict(dns_name=self.hostname,
                 arch=self.arch,
                 tag=self.tag,
                 mem=self.mem,
                 storage=self.storage,
                 cpus=self.cpu_cores)
        return ("hostname:{dns_name} tag:{tag} mem:{mem} arch:{arch}"
                "storage:{storage} cores:{cpus})>").format(**d)


class MaasState:
    """ Represents global MaaS state """

    def __init__(self, maas_client):
        self.maas_client = maas_client
        self._maas_client_nodes = None
        self.start_time = time.time()

    def nodes(self):
        """ Cache MAAS nodes
        """
        elapsed_time = time.time() - self.start_time
        if not self._maas_client_nodes or elapsed_time > 20:
            self._maas_client_nodes = self.maas_client.nodes
            self.start_time = time.time()
        return self._maas_client_nodes

    def invalidate_nodes_cache(self):
        """Force reload on next access"""
        self._maas_client_nodes = None

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

    def machines(self, state=None):
        """Maas Machines

        :param state

        :returns: machines known to Maas, except for juju bootstrap
        machine, matching state type, or all if state=None

        :rtype: list of MaasMachine

        """

        all_machines = [MaasMachine(-1, m) for m in self.nodes()
                        if m['hostname'] != 'juju-bootstrap.maas']
        if state:
            return [m for m in all_machines if m.status == state]
        else:
            return all_machines

    def machines_summary(self):
        """ Returns summary of known machines and their states.
        """
        log.debug("in summary, self.nodes is {}".format(self.nodes()))
        return Counter([MaasMachineStatus(m['status'])
                        for m in self.nodes()])
