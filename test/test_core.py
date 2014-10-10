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
from unittest.mock import ANY, MagicMock, patch, PropertyMock

from cloudinstall import core


@patch('cloudinstall.core.JujuClient')
@patch('cloudinstall.core.MaasAuth')
@patch('cloudinstall.core.MaasClient')
@patch('cloudinstall.core.Config')
class DisplayControllerTestCase(unittest.TestCase):

    def setUp(self):
        self.passwd = 'passwd'
        self.p_pass = PropertyMock(return_value=self.passwd)
        self.mock_opts = MagicMock()

    def test_initialize_multi(self, mock_config, mock_maasclient,
                              mock_maasauth, mock_jujuclient):

        p_yes = PropertyMock(return_value=True)
        type(mock_config()).is_multi = p_yes
        type(mock_config()).juju_api_password = self.p_pass

        dc = core.DisplayController(opts=self.mock_opts)

        dc.initialize()

        mock_jujuclient.assert_called_once_with(url=ANY,
                                                password=self.passwd)
        mock_maasclient.assert_called_with(mock_maasauth())

    def test_initialize_single(self, mock_config, mock_maasclient,
                               mock_maasauth, mock_jujuclient):

        p_no = PropertyMock(return_value=False)
        type(mock_config()).is_multi = p_no
        type(mock_config()).juju_api_password = self.p_pass

        dc = core.DisplayController(opts=self.mock_opts)

        dc.initialize()

        mock_jujuclient.assert_called_once_with(url=ANY,
                                                password=self.passwd)
        assert mock_maasauth.called is False
        assert mock_maasclient.called is False
