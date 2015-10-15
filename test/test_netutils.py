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

from cloudinstall.netutils import get_unique_lxc_network, is_ipv6

log = logging.getLogger('cloudinstall.test_netutils')


class NetUtilsTestCase(unittest.TestCase):
    ipv6 = "2001:470:1f07:cd:216:3eff:fee6:e2da"
    ipv4 = "192.168.1.1"

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

    def test_is_ipv6(self):
        """ Should be an ipv6 address
        """
        self.assertTrue(is_ipv6(self.ipv6))

    def test_is_no_ipv6(self):
        """ Should not be ip6 address
        """
        self.assertFalse(is_ipv6(self.ipv4))
