#!/usr/bin/env python
#
# test_service.py - test cases for classes in service.py
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
import yaml

from cloudinstall.service import Service


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        with open('test/juju-output/juju-status-single-install.yaml') as f:
            status = yaml.load(f.read())
        services = status['services']
        self.services = {s_name: Service(s_name, s_dict) for
                         s_name, s_dict in services.items()}

    def test_get_relations(self):
        "Get relations where they exist"
        glance = self.services['glance']
        self.assertEqual(len(list(glance.relations)), 5)

    def test_no_relations(self):
        "Return empty iterator where no relations exist"
        jujugui = self.services['juju-gui']
        self.assertEqual(len(list(jujugui.relations)), 0)

    def test_empty_relation(self):
        "Return an 'unknown' relation if none is found"
        keystone = self.services['keystone']
        rel = keystone.relation("bogus")
        self.assertEqual(rel.relation_name, "unknown")

    def test_get_one_relation(self):
        "Return a single known relation"
        keystone = self.services['keystone']
        rel = keystone.relation("identity-service")
        self.assertEqual(rel.relation_name, "identity-service")
        self.assertEqual(len(rel.charms), 3)
