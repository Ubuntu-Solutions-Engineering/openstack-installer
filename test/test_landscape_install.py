#!/usr/bin/env python
#
# tests landscape install path in landscape_install.py and multi_install.py
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
from unittest.mock import ANY, MagicMock, patch, PropertyMock

from cloudinstall.multi_install import LandscapeInstallFinal

log = logging.getLogger('cloudinstall.test_landscape_install')


@patch('cloudinstall.multi_install.utils')  # mocks everything in utils
class LandscapeInstallFinalTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_multi_installer = MagicMock()
        self.mock_display_controller = MagicMock()
        self.opts = MagicMock()
        self.loop = MagicMock()

    def make_installer_with_config(self, landscape_creds=None,
                                   maas_creds=None):

        c = MagicMock(name='mock config')
        if landscape_creds is None:
            landscape_creds = dict(admin_name="fakeadminname",
                                   admin_email="fake@email.fake",
                                   system_email="fake@email.system.fake")
        pmcreds = PropertyMock(return_value=landscape_creds)
        type(c).landscape_creds = pmcreds
        if maas_creds is None:
            maas_creds = dict(api_host="fake.host")
        pmcreds = PropertyMock(return_value=maas_creds)
        type(c).maas_creds = pmcreds

        pm_binpath = PropertyMock(return_value='mockbinpath')
        type(c).bin_path = pm_binpath
        pm_cfgpath = PropertyMock(return_value='mockcfgpath')
        type(c).cfg_path = pm_cfgpath

        lif = LandscapeInstallFinal(self.mock_multi_installer,
                                    self.mock_display_controller,
                                    config=c,
                                    opts=self.opts,
                                    loop=self.loop)
        self.installer = lif

    def test_run_configure_not_sudo_user(self, mock_utils):
        """Do not sudo -u $SUDO_USER when running landscape-configure, it will
        be 'root'.
        """
        self.make_installer_with_config()
        mock_utils.get_command_output.return_value = {'status': '',
                                                      'output': ''}
        self.installer.run_configure_script()
        mock_utils.get_command_output.assert_called_with(ANY, timeout=None)

    def test_run_configure_quotes_config_values(self, mock_utils):
        cd = dict(admin_name="fake admin name with spaces",
                  admin_email="itsvalid!@email.fake",
                  system_email="sosthis?@email.system.fake")
        self.make_installer_with_config(landscape_creds=cd)
        mock_utils.get_command_output.return_value = {'status': '',
                                                      'output': ''}
        self.installer.run_configure_script()
        expectedcmdstr = ("mockbinpath/configure-landscape "
                          "--admin-email '{}' "
                          "--admin-name '{}' "
                          "--system-email '{}' "
                          "--maas-host fake.host".format(cd['admin_email'],
                                                         cd['admin_name'],
                                                         cd['system_email']))
        mock_utils.get_command_output.assert_called_with(expectedcmdstr,
                                                         timeout=None)

    def test_run_configure_raises_on_error(self, mock_utils):
        self.make_installer_with_config()
        mock_utils.get_command_output.return_value = {'status': 1,
                                                      'output': 'failure'}
        self.assertRaises(Exception, self.installer.run_configure_script)

    def test_run_deployer_raises_on_error(self, mock_utils):
        self.make_installer_with_config()
        mock_utils.get_command_output.return_value = {'status': 1,
                                                      'output': 'failure'}
        self.assertRaises(Exception, self.installer.run_deployer)

    def test_run_deployer_has_no_timeout(self, mock_utils):
        self.make_installer_with_config()
        mock_utils.get_command_output.return_value = {'status': '',
                                                      'output': 'failure'}
        self.installer.run_deployer()
        mock_utils.get_command_output.assert_called_with(ANY, timeout=None,
                                                         user_sudo=ANY)
