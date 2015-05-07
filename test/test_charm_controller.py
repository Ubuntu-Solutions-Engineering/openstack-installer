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
import unittest
from unittest.mock import MagicMock, patch
from cloudinstall.charms.controller import CharmNovaCloudController

log = logging.getLogger('cloudinstall.test_charms')


def source_tree_template_loader(name):
    p = os.path.join(os.path.dirname(__file__), "../share/templates")
    return Environment(loader=FileSystemLoader(p)).get_template(name)


class TestController(unittest.TestCase):

    def setUp(self):
        self.mock_jujuclient = MagicMock(name='jujuclient')
        self.mock_juju_state = MagicMock(name='juju_state')
        self.mock_ui = MagicMock(name='ui')
        self.mock_config = MagicMock(name='config')

        self.get_config_patcher = patch('cloudinstall.charms.get_charm_config')
        self.mock_get_config = self.get_config_patcher.start()
        self.mock_get_config.return_value = ({}, None)

        self.charm = CharmNovaCloudController(juju=self.mock_jujuclient,
                                              juju_state=self.mock_juju_state,
                                              ui=self.mock_ui,
                                              config=self.mock_config)
        self.ltp = patch('cloudinstall.utils.load_template')
        self.mock_load_template = self.ltp.start()
        self.mock_load_template.side_effect = source_tree_template_loader

    def tearDown(self):
        self.get_config_patcher.stop()
        self.ltp.stop()

    @patch('cloudinstall.utils.spew')
    def test_render_setup_script_single(self, mock_spew):
        self.mock_config.is_single.return_value = True
        self.mock_config.cfg_path = 'fake-cfg-path'
        self.mock_config.getopt.return_value = '10.0.90210.0/24'
        self.charm.render_setup_script()
        name, (path, script_text), kwargs = mock_spew.mock_calls[0]
        self.mock_config.getopt.assert_any_call('lxc_network'),
        self.mock_config.getopt.assert_any_call('openstack_release')
        self.assertEqual(path, 'fake-cfg-path/nova-controller-setup.sh')
        self.assertTrue('--gateway 10.0.90210.1' in script_text)

    @patch('cloudinstall.utils.spew')
    def test_render_setup_script_multi(self, mock_spew):
        self.mock_config.is_single.return_value = False
        self.mock_config.cfg_path = 'fake-cfg-path'

        self.charm.render_setup_script()
        name, (path, script_text), kwargs = mock_spew.mock_calls[0]
        self.mock_config.getopt.assert_called_with('openstack_release')
        self.assertEqual(path, 'fake-cfg-path/nova-controller-setup.sh')
        self.assertTrue('--gateway 10.0.0.1' in script_text)
