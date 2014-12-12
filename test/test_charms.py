#!/usr/bin/env python
#
# tests utils.py
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

from jinja2 import Environment, FileSystemLoader
import logging
import os
import unittest
from unittest.mock import call, MagicMock, patch

from cloudinstall.charms.neutron_openvswitch import CharmNeutronOpenvswitch


log = logging.getLogger('cloudinstall.test_utils')


def source_tree_template_loader(name):
    p = os.path.join(os.path.dirname(__file__), "../share/templates")
    return Environment(loader=FileSystemLoader(p)).get_template(name)


class TestCharmNeutronOpenvswitch(unittest.TestCase):
    def setUp(self):
        self.mock_juju = MagicMock(name='juju')
        self.mock_juju_state = MagicMock(name='juju_state')
        charmbase_str = "cloudinstall.charms.neutron_openvswitch.CharmBase"
        with patch(charmbase_str) as mock_charmbase:
            mock_charmbase.set_relations.return_value = False
            mock_charmbase.is_related.return_value = False
            self.charm = CharmNeutronOpenvswitch(self.mock_juju,
                                                 self.mock_juju_state)

    def test_set_relations_ok(self):
        self.charm.set_relations()

        expected = [call.add_relation('neutron-openvswitch:amqp',
                                      'rabbitmq-server:amqp'),
                    call.add_relation('neutron-openvswitch:neutron-plugin',
                                      'nova-compute:neutron-plugin'),
                    call.add_relation('neutron-openvswitch:neutron-plugin-api',
                                      'neutron-api:neutron-plugin-api')]

        self.assertEqual(self.mock_juju.mock_calls, expected)
