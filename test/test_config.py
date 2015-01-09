#!/usr/bin/env python
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
import unittest
import os.path as path
from tempfile import NamedTemporaryFile

from cloudinstall.config import Config

log = logging.getLogger('cloudinstall.test_config')

USER_DIR = path.expanduser('~')
DATA_DIR = path.join(path.dirname(__file__), 'files')
GOOD_CONFIG = path.join(DATA_DIR, 'good_config.yaml')
BAD_CONFIG = path.join(DATA_DIR, 'bad_config.yaml')


class TestGoodConfig(unittest.TestCase):

    def setUp(self):
        self._temp_conf = Config(GOOD_CONFIG)
        self._temp_conf.load()
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self._temp_conf._config_file = tempf.name
            self._temp_conf.save()
            self.conf = Config(tempf.name)
            self.conf.load()

    def test_save_openstack_password(self):
        """ Save openstack password to config """
        self.conf.setopt('openstack_password', 'pass')
        self.conf.save()
        self.assertTrue('pass' in self.conf.getopt('openstack_password'))

    def test_save_maas_creds(self):
        """ Save maas credentials """
        self.conf.setopt('maascreds', dict(api_host='127.0.0.1',
                                           api_key='1234567'))
        self.conf.save()
        self.assertTrue(
            '127.0.0.1' in self.conf.getopt('maascreds')['api_host'])

    def test_save_landscape_creds(self):
        """ Save landscape credentials """
        self.conf.setopt('landscapecreds',
                         dict(admin_name='foo',
                              admin_email='foo@bar.com',
                              system_email='foo@bar.com',
                              maas_server='127.0.0.1',
                              maas_apikey='123457'))
        self.conf.save()
        self.assertTrue(
            'foo@bar.com' in self.conf.getopt('landscapecreds')['admin_email'])

    def test_save_installer_type(self):
        """ Save installer type """
        self.conf.setopt("install_type", 'multi')
        self.conf.save()
        self.assertTrue('multi' in self.conf.getopt('install_type'))

    def test_cfg_path(self):
        """ Validate current users config path """
        self.assertTrue(
            self.conf.cfg_path == path.join(USER_DIR, '.cloud-install'))

    def test_bin_path(self):
        """ Validate additional tools bin path """
        self.assertTrue(self.conf.bin_path == '/usr/share/openstack/bin')

    def test_juju_environments_path(self):
        """ Validate juju environments path in user dir """
        self.assertTrue(
            self.conf.juju_environments_path == path.join(
                USER_DIR, '.cloud-install/environments.yaml'))


class TestBadConfig(unittest.TestCase):

    def setUp(self):
        self._temp_conf = Config(BAD_CONFIG)
        self._temp_conf.load()
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self._temp_conf._config_file = tempf.name
            self._temp_conf.save()
            self.conf = Config(tempf.name)
            self.conf.load()

    def test_no_openstack_password(self):
        """ No openstack password defined """
        with self.assertRaises(Exception):
            self.conf.openstack_password

    def test_no_landscape_creds(self):
        """ No landscape creds defined """
        with self.assertRaises(Exception):
            self.conf.landscape_creds

    def test_no_installer_type(self):
        """ No installer type defined """
        self.assertFalse(self.conf.is_single)
