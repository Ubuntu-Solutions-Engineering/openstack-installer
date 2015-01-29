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
import yaml
import os.path as path
import argparse
from tempfile import NamedTemporaryFile

from cloudinstall.config import Config
import cloudinstall.utils as utils

log = logging.getLogger('cloudinstall.test_config')

USER_DIR = path.expanduser('~')
DATA_DIR = path.join(path.dirname(__file__), 'files')
GOOD_CONFIG = yaml.load(utils.slurp(path.join(DATA_DIR, 'good_config.yaml')))
BAD_CONFIG = yaml.load(utils.slurp(path.join(DATA_DIR, 'bad_config.yaml')))


def parse_opts(argv):
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument('-i', '--install-only', action='store_true',
                        dest='install_only')
    parser.add_argument('-u', '--uninstall', action='store_true',
                        dest='uninstall')
    parser.add_argument('-c', '--config', type=str, dest='config_file')
    parser.add_argument('-k', '--killcloud', action='store_true',
                        dest='killcloud')
    parser.add_argument('--killcloud-noprompt', action='store_true',
                        dest='killcloud_noprompt')
    parser.add_argument('--openstack-release', default=None,
                        dest='openstack_release')
    parser.add_argument('-a', type=str, default=None)
    parser.add_argument('-r', type=str, default=None, dest='release')
    parser.add_argument('-p', '--placement', action='store_true',
                        dest='edit_placement')
    parser.add_argument('--extra-ppa', nargs='+', dest='extra_ppa')
    parser.add_argument('--upstream-deb', dest='upstream_deb')
    parser.add_argument('--http-proxy', dest='http_proxy')
    parser.add_argument('--https-proxy', dest='https_proxy')
    parser.add_argument('--headless', action='store_true',
                        dest='headless')
    return parser.parse_args(argv)


class TestGoodConfig(unittest.TestCase):

    def setUp(self):
        self._temp_conf = Config(GOOD_CONFIG)
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self.conf = Config(self._temp_conf._config, tempf.name)

    def test_save_openstack_password(self):
        """ Save openstack password to config """
        self.conf.setopt('openstack_password', 'pass')
        self.conf.save()
        self.assertEqual('pass', self.conf.getopt('openstack_password'))

    def test_save_maas_creds(self):
        """ Save maas credentials """
        self.conf.setopt('maascreds', dict(api_host='127.0.0.1',
                                           api_key='1234567'))
        self.conf.save()
        self.assertEqual(
            '127.0.0.1', self.conf.getopt('maascreds')['api_host'])

    def test_save_landscape_creds(self):
        """ Save landscape credentials """
        self.conf.setopt('landscapecreds',
                         dict(admin_name='foo',
                              admin_email='foo@bar.com',
                              system_email='foo@bar.com',
                              maas_server='127.0.0.1',
                              maas_apikey='123457'))
        self.conf.save()
        self.assertEqual(
            'foo@bar.com', self.conf.getopt('landscapecreds')['admin_email'])

    def test_save_installer_type(self):
        """ Save installer type """
        self.conf.setopt("install_type", 'multi')
        self.conf.save()
        self.assertEqual('multi', self.conf.getopt('install_type'))

    def test_cfg_path(self):
        """ Validate current users config path """
        self.assertEqual(
            self.conf.cfg_path, path.join(USER_DIR, '.cloud-install'))

    def test_bin_path(self):
        """ Validate additional tools bin path """
        self.assertEqual(self.conf.bin_path, '/usr/share/openstack/bin')

    def test_juju_environments_path(self):
        """ Validate juju environments path in user dir """
        self.assertEqual(
            self.conf.juju_environments_path,
            path.join(
                USER_DIR, '.cloud-install/juju/environments.yaml'))

    def test_clear_empty_args(self):
        """ Empty cli options are not populated
        in generated config
        """
        cfg_file = path.join(DATA_DIR, 'good_config.yaml')
        cfg = utils.populate_config(parse_opts(['--config', cfg_file]))
        self.assertEqual(True, 'http-proxy' not in cfg)

    def test_config_file_persists(self):
        """ CLI options override options in config file
        """
        cfg_file = path.join(DATA_DIR, 'good_config.yaml')
        cfg = utils.populate_config(
            parse_opts(['--config', cfg_file,
                        '--headless']))
        self.assertEqual(True, cfg['headless'])

    def test_config_file_persists_new_cli_opts(self):
        """ Generated config object appends new options
        passed via cli
        """
        cfg_file = path.join(DATA_DIR, 'good_config.yaml')
        cfg = utils.populate_config(
            parse_opts(['--config', cfg_file,
                        '--install-only',
                        '--killcloud-noprompt']))
        self.assertEqual(True, cfg['install_only'])
        self.assertEqual(True, cfg['killcloud_noprompt'])

    def test_config_overrides_from_cli(self):
        """ Config object item is not overridden
        by unset cli option
        """
        cfg_file = path.join(DATA_DIR, 'good_config.yaml')
        cfg = utils.populate_config(
            parse_opts(['--http-proxy',
                        'http://localhost:2222',
                        '--killcloud-noprompt',
                        '--config', cfg_file]))
        self.assertEqual(cfg['https_proxy'], GOOD_CONFIG['https_proxy'])

    def test_default_opts_not_override_config(self):
        """ Verify that default cli opts that are False
        do not override their config_option whose option
        is True.
        """
        cfg_file = path.join(DATA_DIR, 'good_config.yaml')
        cfg_opts_raw = parse_opts(['--config', cfg_file])
        cfg_opts_raw = vars(cfg_opts_raw)
        self.assertEqual(True, 'headless' not in cfg_opts_raw)

        cfg = utils.populate_config(parse_opts(['--config', cfg_file]))
        self.assertEqual(True, cfg['headless'])

    def test_default_opts_no_config(self):
        """ Verify that default cli opts are sanitized
        and that no options set to False or None exist
        in the config object
        """
        cfg = utils.populate_config(parse_opts([]))
        print(cfg)
        self.assertEqual(True, 'headless' not in cfg)


@unittest.skip
class TestBadConfig(unittest.TestCase):

    def setUp(self):
        self._temp_conf = Config(BAD_CONFIG)
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self.conf = Config(self._temp_conf._config, tempf.name)

    def test_no_openstack_password(self):
        """ No openstack password defined """
        self.assertFalse(self.conf.getopt('openstack_password'))

    def test_no_landscape_creds(self):
        """ No landscape creds defined """
        self.assertFalse(self.conf.getopt('landscapecreds'))

    def test_no_installer_type(self):
        """ No installer type defined """
        self.assertFalse(self.conf.is_single)
