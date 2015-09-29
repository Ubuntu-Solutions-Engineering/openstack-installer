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
import os.path as path
import cloudinstall.utils as utils

log = logging.getLogger('cloudinstall.test_openstack_rc')

USER_DIR = path.expanduser('~')
DATA_DIR = path.join(path.dirname(__file__), 'files')
ADMIN_RC = path.join(DATA_DIR, "openstack-admin-rc")
UBUNTU_RC = path.join(DATA_DIR, "openstack-ubuntu-rc")


class TestOpenstackRC(unittest.TestCase):
    def setUp(self):
        """ read admin rc file
        """
        self.creds = utils.parse_openstack_creds(ADMIN_RC)

    def test_username(self):
        """ Test admin username
        """
        self.assertEqual(self.creds['username'], 'admin')

    def test_password(self):
        """ Test password parsed
        """
        self.assertEqual(self.creds['password'], 'pass')

    def test_tenant_name(self):
        """ Test tenant name is parsed
        """
        self.assertEqual(self.creds['tenant_name'], 'admin')

    def test_auth_url(self):
        """ Test auth url is parsed
        """
        url = self.creds['auth_url']
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.port, 5000)
        self.assertEqual(url.path, '/v2.0')

    def test_region_name(self):
        """ Test region name parsed
        """
        self.assertEqual(self.creds['region_name'], 'RegionOne')
