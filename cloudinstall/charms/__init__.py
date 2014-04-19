#
# charms.py - Charm instructions to Cloud Installer
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

from cloudinstall.juju.client import JujuClient


class CharmBase:
    """ Base charm class """

    charm_name = None

    def __init__(self, machine):
        """ initialize

        :param Machine() machine: Machine to deploy charm to
        """
        self.charm_path = None
        self.exposed = False
        self.machine = machine
        self.client = JujuClient()

    @classmethod
    def name(class_):
        """ Return charm name

        :returns: name of charm
        :rtype: lowercase str
        """
        if class_.charm_name:
            return class_.charm_name
        return class_.__name__.lower()

    def setup(self):
        """ Deploy charm and configuration options

        The default should be sufficient but if more functionality
        is needed this should be overridden.
        """
        self.client.deploy(charm=self.charm_name,
                           machine_id=self.machine.machine_id)


    def set_relations(self):
        """ Setup charm relations

        Override in charm specific.
        """
        pass

    def __repr__(self):
        return self.name()
