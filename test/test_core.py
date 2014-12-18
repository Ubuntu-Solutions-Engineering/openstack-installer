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
from tempfile import NamedTemporaryFile

from cloudinstall import core


@patch('cloudinstall.core.JujuClient')
@patch('cloudinstall.core.connect_to_maas')
@patch('cloudinstall.core.Config')
class DisplayControllerTestCase(unittest.TestCase):

    def setUp(self):
        self.passwd = 'passwd'
        self.p_pass = PropertyMock(return_value=self.passwd)
        tf = NamedTemporaryFile(mode='w+')
        self.p_placementsfilename = PropertyMock(return_value=tf.name)
        self.mock_opts = MagicMock()
        self.get_config_patcher = patch('cloudinstall.charms.get_charm_config')
        self.mock_get_config = self.get_config_patcher.start()
        self.mock_get_config.return_value = ({}, None)

    def tearDown(self):
        self.get_config_patcher.stop()

    def test_initialize_multi(self, mock_config, mock_conn_maas,
                              mock_jujuclient):

        p_yes = PropertyMock(return_value=True)
        type(mock_config()).is_multi = p_yes
        type(mock_config()).juju_api_password = self.p_pass
        type(mock_config()).placements_filename = self.p_placementsfilename
        type(mock_config()).maas_creds = PropertyMock(return_value={})

        mock_conn_maas.return_value = (MagicMock(name='fake maasclient'),
                                       MagicMock(name='fake maas state'))

        dc = core.DisplayController(opts=self.mock_opts)

        dc.initialize()

        mock_jujuclient.assert_called_once_with(url=ANY,
                                                password=self.passwd)
        mock_conn_maas.assert_called_with({})

    def test_initialize_single(self, mock_config, mock_conn_maas,
                               mock_jujuclient):

        p_no = PropertyMock(return_value=False)
        type(mock_config()).is_multi = p_no
        type(mock_config()).juju_api_password = self.p_pass
        type(mock_config()).placements_filename = self.p_placementsfilename

        dc = core.DisplayController(opts=self.mock_opts)

        dc.initialize()

        mock_jujuclient.assert_called_once_with(url=ANY,
                                                password=self.passwd)
        assert mock_conn_maas.called is False
