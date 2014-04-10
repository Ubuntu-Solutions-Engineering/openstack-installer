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

class Machine:
    """ Base machine class """

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
        return Machine(lxc, self.containers.get(lxc, {}))
