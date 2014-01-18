#!/usr/bin/env python

import unittest
import os
import sys
sys.path.insert(0, '../cloudinstall')

from cloudinstall.maas.auth import MaasAuth
from cloudinstall.maas.client import MaasClient
from cloudinstall.utils import randomString

ROOT_USER = os.environ['CI_USER'] if 'CI_USER' in os.environ else 'admin'
AUTH = MaasAuth()

class MaasAuthTest(unittest.TestCase):
    def test_get_api_key(self):
        AUTH.get_api_key(ROOT_USER)
        self.assertEquals(3, len(AUTH.api_key.split(':')))

class MaasClientTest(unittest.TestCase):
    def setUp(self):
        self.c = MaasClient(AUTH)
        self.tag = 'a-test-tag-' + randomString()

    def test_get_tags(self):
        res = self.c.tags
        self.assertGreater(len(res), 0)

    def test_tag_new(self):
        res = self.c.tag_new(self.tag)
        self.assertTrue(res)

    def test_tag_delete(self):
        res = self.c.tag_delete(self.tag)
        self.assertTrue(res)

class MaasClientZoneTest(unittest.TestCase):
    def setUp(self):
        self.c = MaasClient(AUTH)

    def test_new_zone(self):
        res = self.c.zone_new('testzone-' + randomString(), 
                              'zone created in unittest')

    def test_get_zones(self):
        res = self.c.zones
        self.assertEquals(len(res), 0)

if __name__ == '__main__':
    unittest.main()
