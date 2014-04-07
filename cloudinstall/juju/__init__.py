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


class JujuState:
    def __init__(self, raw_yaml):
        """ Builds a JujuState from a file-like object containing the raw
        output from __juju status__

        :param raw_yaml: YAML object
        """
        self._yaml = yaml.load(raw_yaml)

    def id_for_machine_no(self, no):
        """ Returns id of a machine

        :param no: machine number
        :type no: int
        :returns: instance-id of machine
        :rtype: str
        """
        return self._yaml['machines'][no]['instance-id']

    @property
    def machines(self):
        """ Machines property

        :returns: machines known to juju
        :rtype: list
        """
        return self._yaml['machines'].items()

    def machine(self, id):
        """ Returns instance-id of machine

        :param id: machine id
        :type id: int
        :returns: instance-id
        :rtype: str
        """
        for no, m in self.machines:
            if m['instance-id'] == id:
                m['machine_no'] = no
                return m

    @property
    def services(self):
        """ Juju services property

        :returns: list of {servicename: nodecount}
        :rtype: list
        """
        ret = {}
        for svc, contents in self._yaml.get('services', {}).items():
            ret[svc] = len(contents.get('units', []))
        return ret

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

    @property
    def containers(self):
        """ A map of container-ids

        :returns: [{"1/lxc/0": ([charm name], [unit name])]
        :rtype: list
        """
        def by_machine_name(unit):
            return unit['machine']

        def is_lxc(id_):
            return 'lxc' in id_
        return self._build_unit_map(by_machine_name, allow_id=is_lxc)

    def container(self, machine, id_):
        """ Inspect a container

        :param machine: id of machine to inspect
        :type machine: int
        :param id_: lxc container id
        :type id_: int
        :returns: Returns a dictionary of the container information for
                  specific machine and lxc id.
        :rtype: dict
        """
        lxc = "%s/lxc/%s" % (machine, id_)
        return self._yaml["machines"][machine]["containers"][lxc]
