#
# service.py - Juju Services and Units
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

""" Represents a Juju service """


class Unit:
    """ Unit class """

    def __init__(self, unit_name, unit):
        self.unit_name = unit_name
        self.unit = unit

    @property
    def agent_state(self):
        """ Unit's agent state

        :returns: agent state
        :rtype: str
        """
        return self.unit.get('agent-state', 'unknown')

    @property
    def machine_id(self):
        """ Associate machine for unit

        :returns: machine id
        :rtype: str
        """
        return self.unit.get('machine', '-1')

    @property
    def public_address(self):
        """ Public address of unit

        :returns: address of unit
        :rtype: str
        """
        return self.unit.get('public-address', '0.0.0.0')

    def __repr__(self):
        return "<Unit: {name} " \
            "Machine: {machine}>".format(name=self.unit_name,
                                         machine=self.machine_id)


class Relation:
    """ Relation class """

    def __init__(self, relation_name, charms):
        self.relation_name = relation_name
        self.charms = charms


class Service:
    """ Service class """

    def __init__(self, service_name, service):
        self.service_name = service_name
        self.service = service

    @property
    def charm(self):
        """ Charm

        :returns: Charm Path
        :rtype: str
        """
        return self.service.get('charm', '')

    @property
    def exposed(self):
        """ Exposed

        :returns: if service is exposed
        :rtype: bool
        """

    def unit(self, name):
        """ Single unit entry

        :params str name: name of unit
        :returns: a Unit entry
        :rtype: Unit()
        """
        u = list(filter(lambda u: u.unit_name == name, self.units))[0]
        if u:
            return u
        return Unit('unknown', [])

    @property
    def units(self):
        """ Service units

        :returns: list associated units for service
        :rtype: Unit()
        """
        for unit_name, units in self.service.get('units', {}).items():
            yield Unit(unit_name, units)


    @property
    def relations(self):
        """ Service relations

        :returns: list of relations for service
        :rtype: Relation()
        """
        for relation_name, relation in \
            self.service.get('relations', {}).items():
            yield Relation(relation_name, relation)


    def __repr__(self):
        return "<Service: {name} " \
            "Units: {units}>".format(name=self.service_name,
                                     units=list(self.units))
