#!/usr/bin/env python
#
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

import unittest
from unittest.mock import MagicMock, patch

from cloudinstall.multi_install import MultiInstallNewMaas, MaasInstallError
from cloudinstall.config import Config
from tempfile import NamedTemporaryFile


class MultiInstallNewMaasTestCase(unittest.TestCase):

    def setUp(self):
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self.conf = Config({}, tempf.name)
        self.conf.setopt('openstack_password', 'ampersand&')

    def make_installer(self, loop=None, dc=None):

        if dc is None:
            dc = MagicMock(name="display_controller")
        if loop is None:
            loop = MagicMock(name="loop")

        self.installer = MultiInstallNewMaas(
            loop, dc, self.conf)

    def _create_superuser(self, raises):
        expected = ("maas-region-admin createadmin --username root "
                    "--password 'ampersand&' "
                    "--email root@example.com")

        self.make_installer()
        with patch('cloudinstall.multi_install.utils') as mock_utils:
            if raises:
                mock_utils.get_command_output.return_value = {'status': -1}
                self.assertRaises(MaasInstallError,
                                  self.installer.create_superuser)
            else:
                mock_utils.get_command_output.return_value = {'status': 0}
                self.installer.create_superuser()
                mock_utils.get_command_output.assert_called_with(expected)

    def test_create_superuser_raises(self):
        self._create_superuser(True)

    def test_create_superuser_ok(self):
        self._create_superuser(False)
