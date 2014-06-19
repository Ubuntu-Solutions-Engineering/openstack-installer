#
# compute.py - Nova Compute Charm instructions
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
from cloudinstall.charms import CharmBase, DisplayPriorities
from cloudinstall.pegasus import poll_state

log = logging.getLogger('cloudinstall.charms.compute')


class CharmNovaCompute(CharmBase):
    """ Openstack Nova Compute directives """

    charm_name = 'nova-compute'
    display_name = 'Nova Compute Node'
    display_priority = DisplayPriorities.Compute
    related = ['mysql', 'glance', 'nova-cloud-controller']
    isolate = True
    constraints = {'mem': '4G',
                   'root-disk': '40G'}
    allow_multi_units = True

    def set_relations(self):
        super(CharmNovaCompute, self).set_relations()
        juju, _ = poll_state()
        service = juju.service(self.charm_name)
        has_amqp = list(filter(lambda r: 'amqp' in r.relation_name,
                        service.relations))
        if len(has_amqp) == 0:
            log.debug("Setting amqp relation for compute.")
            ret = self.client.add_relation("{c}:amqp".format(
                                           c=self.charm_name),
                                           "rabbitmq-server:amqp")
            if ret:
                log.error("Problem relating nova-compute to rabbitmq")
                return True
            return False

__charm_class__ = CharmNovaCompute
