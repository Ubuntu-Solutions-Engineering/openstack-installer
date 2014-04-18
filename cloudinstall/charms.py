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


class Charm:
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

    def deploy(self):
        """ Deploy charm, setup relations, and configuration options

        Override in charm specific.
        """
        raise NotImplementedError

    def set_relations(self):
        """ Set charm relations

        Override in charm specific
        """
        raise NotImplementedError


class CharmKeystone(Charm):
    """ Openstack Keystone directives """

    charm_name = 'keystone'

    def deploy(self):
        self.client.deploy(charm=self.charm_name,
                           machine_id=self.machine.machine_id)

    def set_relations(self):
        self.client.add_relation(endpoint_a=self.charm_name,
                                 endpoint_b='mysql')


class CharmNovaCloudController(Charm):
    """ Openstack Nova Cloud Controller directives """

    charm_name = 'nova-cloud-controller'

    def deploy(self):
        self.client.deploy(charm=self.charm_name,
                           machine_id=self.machine.machine_id)

    def set_relations(self):
        for c in ['mysql', 'rabbitmq-server', 'glance', 'keystone']:
            self.client.add_relation(endpoint_a=self.charm_name,
                                     endpoint_b=c)


class CharmNovaCompute(Charm):
    """ Openstack Nova Compute directives """

    charm_name = 'nova-compute'

    def deploy(self):
        self.client.deploy(charm=self.charm_name,
                           machine_id=self.machine.machine_id)

    def set_relations(self):
        for c in ['mysql', 'rabbitmq-server', 'glance', 'nova-cloud-controller']:
            self.client.add_relation(endpoint_a=self.charm_name,
                                     endpoint_b=c)


class CharmGlance(Charm):
    """ Openstack Glance directives """

    charm_name = 'glance'

    def deploy(self):
        self.client.deploy(charm=self.charm_name,
                           machine_id=self.machine.machine_id)

    def set_relations(self):
        for c in ['mysql', 'keystone']:
            self.client.add_relation(endpoint_a=self.charm_name,
                                     endpoint_b=c)


class CharmHorizon(Charm):
    """ Openstack Horizon directives """

    charm_name = 'openstack-dashboard'

    def deploy(self):
        self.client.deploy(charm=self.charm_name,
                           machine_id=self.machine.machine_id)

    def set_relations(self):
        for c in ['keystone']:
            self.client.add_relation(endpoint_a=self.charm_name,
                                     endpoint_b=c)
