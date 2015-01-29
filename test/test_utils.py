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
from unittest.mock import patch, PropertyMock
import yaml

from cloudinstall.utils import render_charm_config, merge_dicts, slurp
from cloudinstall.config import Config
from tempfile import NamedTemporaryFile


log = logging.getLogger('cloudinstall.test_utils')

DATA_DIR = os.path.join(os.path.dirname(__file__), 'files')


def source_tree_template_loader(name):
    p = os.path.join(os.path.dirname(__file__), "../share/templates")
    return Environment(loader=FileSystemLoader(p)).get_template(name)


@patch('cloudinstall.utils.spew')
class TestRenderCharmConfig(unittest.TestCase):

    def setUp(self):
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self.config = Config({}, tempf.name)

        type(self.config).cfg_path = PropertyMock(return_value='fake_cfg_path')
        self.config.setopt('openstack_password', 'fake_pw')
        self.ltp = patch('cloudinstall.utils.load_template')
        self.mock_load_template = self.ltp.start()
        self.mock_load_template.side_effect = source_tree_template_loader

    def tearDown(self):
        self.ltp.stop()

    def _do_test_osrel(self, optsvalue, expected, mockspew):
        "check that opts.openstack_release is rendered correctly"
        self.config.setopt('openstack_release', optsvalue)

        render_charm_config(self.config)
        (fake_path, generated_yaml), kwargs = mockspew.call_args
        d = yaml.load(generated_yaml)
        print(d)
        for oscharmname in ['nova-cloud-controller', 'glance',
                            'openstack-dashboard', 'keystone', 'swift-proxy']:
            if expected is None:
                self.assertTrue(oscharmname not in d or
                                'openstack-origin' not in d[oscharmname])
            else:
                self.assertEqual(d[oscharmname]['openstack-origin'], expected)

    def test_render_openstack_release_default(self, mockspew):
        self._do_test_osrel(None, None, mockspew)

    def test_render_openstack_release_given(self, mockspew):
        with patch('cloudinstall.utils.platform.dist') as mock_dist:
            mock_dist.return_value = ('', '', 'willing')
            self._do_test_osrel('klaxon', 'cloud:willing-klaxon', mockspew)

    def _do_test_multiplier(self, is_single, mockspew, expected=None):
        if is_single:
            self.config.setopt('install_type', 'Single')
        else:
            self.config.setopt('install_type', 'Multi')
        self.config.setopt('openstack_release', 'klaxon')
        render_charm_config(self.config)
        (fake_path, generated_yaml), kwargs = mockspew.call_args
        d = yaml.load(generated_yaml)
        wmul = d['nova-cloud-controller'].get('worker-multiplier', None)
        self.assertEqual(wmul, expected)
        wmul = d['glance'].get('worker-multiplier', None)
        self.assertEqual(wmul, expected)
        wmul = d['keystone'].get('worker-multiplier', None)
        self.assertEqual(wmul, expected)

    def test_render_worker_multiplier_multi(self, mockspew):
        self._do_test_multiplier(False, mockspew)

    def test_render_worker_multiplier_single(self, mockspew):
        self._do_test_multiplier(True, mockspew, expected=1)

    def test_charmconfig_custom_merge(self, mockspew):
        """ Verify rightmost custom charm config dictionary
        does not overwrite untouched items in rendered
        charmconfig
        """
        charm_custom = {'swift-proxy': {'replicas': 15},
                        'mysql': {'dataset-size': '2048M'}}
        charm_conf = yaml.load(slurp(os.path.join(DATA_DIR, 'charmconf.yaml')))
        merged_dicts = merge_dicts(charm_conf, charm_custom)
        self.assertEqual(merged_dicts['mysql']['max-connections'], 25000)
        self.assertEqual(merged_dicts['swift-proxy']['zone-assignment'],
                         'auto')
