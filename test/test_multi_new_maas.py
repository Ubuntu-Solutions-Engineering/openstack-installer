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

from cloudinstall.multi_install import MultiInstallNewMaas


class MultiInstallNewMaasTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def make_installer(self, opts=None, dc=None, config=None):
        if opts is None:
            opts = MagicMock(name="opts")
        if dc is None:
            dc = MagicMock(name="display_controller")
        if config is None:
            config = MagicMock(name="config")

        self.installer = MultiInstallNewMaas(opts, dc, config=config)

    def _create_superuser(self, raises):
        c = MagicMock(name="config")
        c.openstack_password = "ampersand&"

        expected = ("maas-region-admin createadmin --username root "
                    "--password 'ampersand&' "
                    "--email root@example.com")

        self.make_installer(config=c)
        with patch('cloudinstall.multi_install.utils') as mock_utils:
            if raises:
                mock_utils.get_command_output.return_value = {'status': -1}
                self.assertRaises(self.installer.create_superuser)
            else:
                mock_utils.get_command_output.return_value = {'status': 0}
                self.installer.create_superuser()
                mock_utils.get_command_output.assert_called_with(expected)

    def test_create_superuser_raises(self):
        self._create_superuser(True)

    def test_create_superuser_ok(self):
        self._create_superuser(False)
