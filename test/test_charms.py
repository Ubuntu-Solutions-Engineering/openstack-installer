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
from unittest.mock import ANY, call, MagicMock, patch

from cloudinstall.charms import CharmBase
from cloudinstall.charms.neutron_openvswitch import CharmNeutronOpenvswitch


log = logging.getLogger('cloudinstall.test_utils')


def source_tree_template_loader(name):
    p = os.path.join(os.path.dirname(__file__), "../share/templates")
    return Environment(loader=FileSystemLoader(p)).get_template(name)


class TestCharmBase(unittest.TestCase):

    def setUp(self):
        self.mock_jujuclient = MagicMock(name='jujuclient')
        self.mock_juju_state = MagicMock(name='juju_state')
        self.mock_ui = MagicMock(name='ui')
        self.mock_config = MagicMock(name='config')

        self.get_config_patcher = patch('cloudinstall.charms.get_charm_config')
        self.mock_get_config = self.get_config_patcher.start()
        self.mock_get_config.return_value = ({}, None)

        self.charm = CharmBase(juju=self.mock_jujuclient,
                               juju_state=self.mock_juju_state,
                               ui=self.mock_ui,
                               config=self.mock_config)

    def tearDown(self):
        self.get_config_patcher.stop()

    def test_subordinate_deploy_success(self):
        self.charm.subordinate = True
        self.charm.charm_name = 'fake'
        self.charm.deploy('fake mspec')
        self.mock_jujuclient.deploy.assert_called_with('fake', 'fake',
                                                       0, ANY, None,
                                                       None)


class TestCharmNeutronOpenvswitch(unittest.TestCase):

    def setUp(self):
        self.mock_jujuclient = MagicMock(name='jujuclient')
        self.mock_juju_state = MagicMock(name='juju_state')
        self.mock_ui = MagicMock(name='ui')
        self.mock_config = MagicMock(name='config')

        charmbase_str = "cloudinstall.charms.neutron_openvswitch.CharmBase"
        with patch(charmbase_str) as mock_charmbase:
            mock_charmbase.set_relations.return_value = False
            mock_charmbase.is_related.return_value = False
            self.charm = CharmNeutronOpenvswitch(
                juju=self.mock_jujuclient,
                juju_state=self.mock_juju_state,
                ui=self.mock_ui,
                config=self.mock_config)

    def test_set_relations_ok(self):
        self.charm.set_relations()

        expected = [call.add_relation('neutron-openvswitch:amqp',
                                      'rabbitmq-server:amqp'),
                    call.add_relation('neutron-openvswitch:neutron-plugin',
                                      'nova-compute:neutron-plugin'),
                    call.add_relation('neutron-openvswitch:neutron-plugin-api',
                                      'neutron-api:neutron-plugin-api')]

        self.assertEqual(self.mock_jujuclient.mock_calls, expected)
