#!/usr/bin/env python
#
# Copyright 2015 Canonical, Ltd.
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
from importlib import import_module
import pkgutil
import unittest
from unittest.mock import ANY, MagicMock, patch

import cloudinstall.utils as utils
import cloudinstall.charms
from cloudinstall.charms import CharmBase, CharmQueue, CharmQueueRelationsError
from cloudinstall.charms.neutron_openvswitch import CharmNeutronOpenvswitch
from cloudinstall.charms.compute import CharmNovaCompute
from cloudinstall.charms.glance import CharmGlance
from cloudinstall.charms.mysql import CharmMysql
from cloudinstall.charms.ntp import CharmNtp

log = logging.getLogger('cloudinstall.test_charms')


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


class PrepCharmTest(unittest.TestCase):

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


class TestCharmKeystone(PrepCharmTest):

    def test_missing_agent_state(self):
        """ Checks deploy returns False if agent_state is None/missing """
        ms = MagicMock(name='mock_server')
        self.mock_juju_state.service.return_value = ms
        rv = self.charm.wait_for_agent(['mysql'])
        self.assertFalse(rv)


class TestCharmRelations(unittest.TestCase):

    """ Use NovaCompute to determine if certain relations
    are supported as it contains an optional charm relation.

    NovaCompute includes an optional relation for ceilometer, this
    class will test to make sure that relation is dropped
    since that service is unavailable in this test.
    """

    def setUp(self):
        self.mock_jujuclient = MagicMock(name='jujuclient')
        self.mock_juju_state = MagicMock(name='juju_state')
        self.mock_ui = MagicMock(name='ui')
        self.mock_config = MagicMock(name='config')

        self.deployed_charms = [CharmNtp, CharmNovaCompute, CharmGlance,
                                CharmMysql]

        self.charm = CharmQueue(
            ui=self.mock_ui,
            config=self.mock_config,
            juju=self.mock_jujuclient,
            juju_state=self.mock_juju_state,
            deployed_charms=self.deployed_charms)

        self.expected_relation = [('mysql:shared-db',
                                   'nova-compute:shared-db'),
                                  ('nova-compute:image-service',
                                   'glance:image-service'),
                                  ('ntp:juju-info', 'nova-compute:juju-info'),
                                  ('mysql:shared-db', 'glance:shared-db')]

        self.unexpected_relation = [('nova-compute:nova-ceilometer',
                                     'ceilometer-agent:nova-ceilometer')]

    def test_expected_relations(self):
        """ Test valid relations are provided """
        valid_relations = self.charm.filter_valid_relations()
        self.assertEqual(self.expected_relation, valid_relations)

    def test_unexpected_relations(self):
        """ Test invalid relations are removed """
        valid_relations = self.charm.filter_valid_relations()
        self.assertNotIn(self.unexpected_relation, valid_relations)

    def test_watch_relations_exception(self):
        """ Verifies watch_relations croaks on failed add_relation """
        juju = self.mock_jujuclient

        juju.add_relation.side_effect = Exception('Failed to add relations')

        charm_q = CharmQueue(
            ui=self.mock_ui,
            config=self.mock_config,
            juju=juju,
            juju_state=self.mock_juju_state,
            deployed_charms=self.deployed_charms)
        # TODO: Test expected exception msg
        self.assertRaises(Exception, charm_q.watch_relations)


class TestCharmPlugin(unittest.TestCase):

    def setUp(self):
        cur_path = os.path.abspath(os.path.dirname(__file__))
        self.charm_path = os.path.join(cur_path, 'files/charm_plugins')
        self.charm_modules = [import_module('cloudinstall.charms.' + mname)
                              for (_, mname, _) in
                              pkgutil.iter_modules(
                                  cloudinstall.charms.__path__)]
        self.charm_sys_path = '/usr/share/openstack/cloudinstall/charms'

    def test_override_sys_charm(self):
        """ Check that a system charm is overridden installed charm
        """
        charms = utils.load_ext_charms(self.charm_path, self.charm_modules)
        horizon_charm = [x for x in
                         charms if
                         x.__charm_class__.name() == "openstack-dashboard"]
        charm_path = os.path.dirname(horizon_charm[0].__file__)
        self.assertNotEqual(charm_path, self.charm_sys_path)

    def test_loaded_charm(self):
        """ Check for custom charm plugin
        """
        charms = utils.load_ext_charms(self.charm_path, self.charm_modules)
        charm = [x for x in
                 charms if
                 x.__charm_class__.name() == "bitlbee"]
        self.assertEqual(charm[0].__charm_class__.name(), "bitlbee")
