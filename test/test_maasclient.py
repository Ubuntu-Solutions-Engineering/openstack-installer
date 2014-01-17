#!/usr/bin/env python

import unittest
import os
import sys
sys.path.insert(0, '../cloudinstall')

from cloudinstall.maas.auth import MaasAuth
from cloudinstall.maas.client import MaasClient

ROOT_USER = os.environ['CI_USER'] if 'CI_USER' in os.environ else 'admin'
AUTH = MaasAuth()

class MaasAuthTest(unittest.TestCase):
    def test_get_api_key(self):
        AUTH.get_api_key(ROOT_USER)
        self.assertEquals(3, len(AUTH.api_key.split(':')))

class MaasClientTest(unittest.TestCase):
    def setUp(self):
        self.c = MaasClient(AUTH)

    def test_get_tags(self):
        res = self.c.tags
        self.assertEquals(3, len(res))

    def test_ensure_tag(self):
        tag = 'a-test-tag'
        res = self.c.ensure_tag(tag)
        self.assertTrue(res)

if __name__ == '__main__':
    unittest.main()
