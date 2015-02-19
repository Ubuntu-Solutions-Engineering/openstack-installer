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
from cloudinstall.placement.controller import AssignmentType

log = logging.getLogger('cloudinstall.charms.compute')


class CharmNovaCompute(CharmBase):
    """ Openstack Nova Compute directives """

    charm_name = 'nova-compute'
    charm_rev = 14
    display_name = 'Compute'
    menuable = True
    display_priority = DisplayPriorities.Compute
    related = ['mysql', 'glance', 'nova-cloud-controller']
    isolate = True
    constraints = {'mem': 4096,
                   'root-disk': 40960}
    allow_multi_units = True
    allowed_assignment_types = [AssignmentType.BareMetal,
                                AssignmentType.KVM]

    def set_relations(self):
        if not self.wait_for_agent(['nova-cloud-controller']):
            return True

        for charm in self.related:
            log.debug("{1} adding relation to {0}".format(
                charm, self.display_name))
            try:
                if "mysql" in charm:
                    rv = self.juju.add_relation(
                        "{0}:shared-db".format(self.charm_name),
                        "{0}:shared-db".format(charm))
                    log.debug("add_relation (shared-db) "
                              "returned {}".format(rv))
                else:
                    self.juju.add_relation(self.charm_name,
                                           charm)
                    log.debug("add_relation returned {}".format(rv))
            except:
                log.exception("{0} not ready for relation".format(charm))
                return True

        service = self.juju_state.service(self.charm_name)
        has_amqp = list(filter(lambda r: 'amqp' in r.relation_name,
                        service.relations))
        if len(has_amqp) == 0:
            log.debug("Setting amqp relation for compute.")
            try:
                self.juju.add_relation("{c}:amqp".format(
                                       c=self.charm_name),
                                       "rabbitmq-server:amqp")
            except:
                log.exception("Not ready to set amqp relation.")
                return True
            return False
        return False

__charm_class__ = CharmNovaCompute
