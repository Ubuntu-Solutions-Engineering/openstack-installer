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

import logging
import unittest
from unittest.mock import MagicMock, PropertyMock

from cloudinstall.config import Config
from cloudinstall.juju import JujuState
from cloudinstall.service import Service

log = logging.getLogger('cloudinstall.test_core')


class JujuStateTestCase(unittest.TestCase):

    """ Tests JujuState's services ready routines
    """

    def setUp(self):
        self.conf = Config({}, save_backups=False)
        self.mock_ui = MagicMock(name='ui')
        self.mock_log = MagicMock(name='log')
        self.mock_loop = MagicMock(name='loop')

        self.services_ready = [
            Service('keystone',
                    {'Units': {'fake': {'AgentState': 'started'}}}),
            Service('nova-compute',
                    {'Units': {'fake': {'AgentState': 'started'}}}),
        ]

        self.services_some_ready = [
            Service('keystone',
                    {'Units': {'fake': {'AgentState': 'started'}}}),
            Service('nova-compute',
                    {'Units': {'fake2': {'AgentState': 'started'}}}),
            Service('nova-cloud-controller',
                    {'Units': {'fake3': {'AgentState': 'installing'}}}),
            Service('glance',
                    {'Units': {'fake4': {'AgentState': 'allocating'}}}),
        ]

    def test_services_ready(self):
        """ Verifies all ready services  """
        juju_state = JujuState(juju=MagicMock())
        services = PropertyMock(return_value=self.services_ready)
        type(juju_state).services = services

        not_ready = [(a, b) for a, b in juju_state.get_agent_states()
                     if b != 'started']

        self.assertEqual(len(not_ready), 0)

    def test_some_services_ready(self):
        """ Verifies some ready services == not_ready list """
        juju_state = JujuState(juju=MagicMock())
        services = PropertyMock(return_value=self.services_some_ready)
        type(juju_state).services = services
        not_ready = [(a, b) for a, b in juju_state.get_agent_states()
                     if b != 'started']
        self.assertEqual(len(not_ready), 2)
        self.assertFalse(juju_state.all_agents_started())
