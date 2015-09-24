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

import unittest
from unittest.mock import MagicMock, patch, call

from cloudinstall.controllers.install import MultiInstall
from cloudinstall.config import Config
from tempfile import NamedTemporaryFile


class MultiInstallTestCase(unittest.TestCase):

    def setUp(self):
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self.conf = Config({}, tempf.name, save_backups=False)

        dc = MagicMock(name="display_controller")
        loop = MagicMock(name="loop")
        self.installer = MultiInstall(loop, dc, self.conf)

    @patch('cloudinstall.utils.get_command_output')
    def test_add_bootstrap_to_no_proxy(self, mock_gco):
        minyaml = "machines: {\"0\": {\"dns-name\": \"100.100.100.100\"}}"
        current_env = "maas-server.ip"
        mock_gco.side_effect = [dict(status=0, output=minyaml),
                                dict(status=0, output=current_env),
                                dict(status=0, output='ignore')]
        with patch.object(self.conf, 'juju_home') as mock_jh:
            mock_jh.return_value = 'JH'
            self.installer.add_bootstrap_to_no_proxy()

        set_call_arg = ('JH juju set-env no-proxy='
                        '{},100.100.100.100'.format(current_env))
        expected = [call('JH juju status', timeout=None, user_sudo=True),
                    call('JH juju get-env no-proxy', timeout=None,
                         user_sudo=True),
                    call(set_call_arg,
                         timeout=None, user_sudo=True)]
        self.assertEqual(mock_gco.mock_calls, expected)
