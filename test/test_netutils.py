#!/usr/bin/env python
#
# tests netutils.py
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

import logging
import unittest
from unittest.mock import patch

from cloudinstall.netutils import get_unique_lxc_network

log = logging.getLogger('cloudinstall.test_netutils')


class NetUtilsTestCase(unittest.TestCase):

    @patch('cloudinstall.netutils.check_output')
    def test_get_unique_lxc_network(self, mock_check_output):
        mock_check_output.return_value = ""
        s = get_unique_lxc_network()
        self.assertEqual(s, "10.0.6.0/24")

        mock_check_output.side_effect = ['1', '']
        s = get_unique_lxc_network()
        self.assertEqual(s, "10.0.7.0/24")

        mock_check_output.side_effect = ['1', '2', '3', '']
        s = get_unique_lxc_network()
        self.assertEqual(s, "10.0.9.0/24")
