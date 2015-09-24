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

import errno
from jinja2 import Environment, FileSystemLoader
import logging
import os
from subprocess import PIPE
from tempfile import NamedTemporaryFile
import unittest
from unittest.mock import patch, PropertyMock
import yaml


from cloudinstall.utils import (render_charm_config,
                                merge_dicts, slurp, spew, get_command_output)
from cloudinstall.config import Config


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
            self.config = Config({}, tempf.name, save_backups=False)

        type(self.config).cfg_path = PropertyMock(return_value='fake_cfg_path')
        self.config.setopt('openstack_password', 'fake_pw')
        self.ltp = patch('cloudinstall.utils.load_template')
        self.mock_load_template = self.ltp.start()
        self.mock_load_template.side_effect = source_tree_template_loader

    def tearDown(self):
        self.ltp.stop()

    def _do_test_osrel(self, series, optsvalue, expected, mockspew):
        "check that opts.openstack_release is rendered correctly"
        self.config.setopt('openstack_release', optsvalue)
        self.config.setopt('ubuntu_series', series)

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

    def test_render_openstack_release_given(self, mockspew):
        self._do_test_osrel('trusty', 'klaxon',
                            'cloud:trusty-klaxon', mockspew)

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

    def test_charmconfig_custom_overwrite(self, mockspew):
        """ Verify complex yaml can safely overwrite existing defined keys
        """
        charm_conf = yaml.load(slurp(os.path.join(DATA_DIR, 'charmconf.yaml')))
        charm_conf_custom = yaml.load(slurp(
            os.path.join(DATA_DIR, 'charmconf-deepchainmap-fail.yaml')))
        merged_dicts = merge_dicts(charm_conf, charm_conf_custom)
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            spew(tempf.name, yaml.safe_dump(
                merged_dicts, default_flow_style=False))
            modified_charm_conf = yaml.load(slurp(tempf.name))
            self.assertEqual(modified_charm_conf['mysql']['dataset-size'],
                             '512M')
            self.assertEqual(modified_charm_conf['swift-storage']['zone'],
                             1)


@patch('cloudinstall.utils.os.environ')
@patch('cloudinstall.utils.Popen')
class TestGetCommandOutput(unittest.TestCase):

    def test_get_command_output_timeout(self, mock_Popen, mock_env):
        mock_env.copy.return_value = {'FOO': 'bazbot'}
        mock_Popen.return_value.communicate.return_value = (bytes(), bytes())
        get_command_output("fake", timeout=20)
        mock_Popen.assert_called_with("timeout 20s fake", shell=True,
                                      stdout=PIPE, stderr=PIPE,
                                      bufsize=-1,
                                      env={'LC_ALL': 'C',
                                           'FOO': 'bazbot'},
                                      close_fds=True)

    def test_get_command_output_user_sudo(self, mock_Popen, mock_env):
        mock_env.copy.return_value = {'FOO': 'bazbot'}
        outb, errb = bytes('out', 'utf-8'), bytes('err', 'utf-8')
        mock_Popen.return_value.communicate.return_value = (outb, errb)
        mock_Popen.return_value.returncode = 4747
        with patch('cloudinstall.utils.install_user') as mock_install_user:
            mock_install_user.return_value = 'fakeuser'
            rv = get_command_output("fake", user_sudo=True)
            self.assertEqual(rv, dict(output='out', err='err',
                                      status=4747))

        mock_Popen.assert_called_with("sudo -E -H -u fakeuser fake",
                                      shell=True,
                                      stdout=PIPE, stderr=PIPE,
                                      bufsize=-1,
                                      env={'LC_ALL': 'C',
                                           'FOO': 'bazbot'},
                                      close_fds=True)

    def test_get_command_output_raises(self, mock_Popen, mock_env):
        err = OSError()
        err.errno = errno.ENOENT
        mock_Popen.side_effect = err
        rv = get_command_output('foo')
        self.assertEqual(rv, dict(ret=127, output="", err=""))

        mock_Popen.side_effect = OSError()
        with self.assertRaises(OSError):
            get_command_output('foo')
