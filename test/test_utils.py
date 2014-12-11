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
from unittest.mock import MagicMock, patch
import yaml

from cloudinstall.utils import render_charm_config


log = logging.getLogger('cloudinstall.test_utils')


def source_tree_template_loader(name):
    p = os.path.join(os.path.dirname(__file__), "../share/templates")
    return Environment(loader=FileSystemLoader(p)).get_template(name)


@patch('cloudinstall.utils.spew')
class TestRenderCharmConfig(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock()
        self.config.is_single = False
        self.config.cfg_path = 'fake_cfg_path'

        self.ltp = patch('cloudinstall.utils.load_template')
        self.mock_load_template = self.ltp.start()
        self.mock_load_template.side_effect = source_tree_template_loader

    def tearDown(self):
        self.ltp.stop()

    def _do_test_osrel(self, optsvalue, expected, mockspew):
        "check that opts.openstack_release is rendered correctly"
        opts = MagicMock()
        opts.openstack_release = optsvalue

        render_charm_config(self.config, opts)
        (fake_path, generated_yaml), kwargs = mockspew.call_args
        d = yaml.load(generated_yaml)
        for oscharmname in ['nova-cloud-controller', 'glance',
                            'openstack-dashboard', 'keystone', 'swift-proxy']:
            self.assertEqual(d[oscharmname]['openstack-origin'],
                             expected)

    def test_render_openstack_release_default(self, mockspew):
        self._do_test_osrel(None, 'distro', mockspew)

    def test_render_openstack_release_given(self, mockspew):
        with patch('cloudinstall.utils.platform.dist') as mock_dist:
            mock_dist.return_value = ('', '', 'willing')
            self._do_test_osrel('klaxon', 'cloud:willing-klaxon', mockspew)

    def _do_test_multiplier(self, is_single, mockspew, expected=None):
        self.config.is_single = is_single
        render_charm_config(self.config, MagicMock(openstack_release='klaxon'))
        (fake_path, generated_yaml), kwargs = mockspew.call_args
        log.debug("genyaml i s {}".format(generated_yaml))
        d = yaml.load(generated_yaml)
        import pprint
        log.debug('d is {}'.format(pprint.pformat(d)))
        wmul = d['nova-cloud-controller'].get('worker-multiplier', None)
        self.assertEqual(wmul, expected)

    def test_render_worker_multiplier_multi(self, mockspew):
        self._do_test_multiplier(False, mockspew)

    def test_render_worker_multiplier_single(self, mockspew):
        self._do_test_multiplier(True, mockspew, expected=1)
