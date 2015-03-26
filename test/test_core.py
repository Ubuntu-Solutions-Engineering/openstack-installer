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
from cloudinstall.core import Controller
from cloudinstall.juju import JujuState
from cloudinstall.service import Service

log = logging.getLogger('cloudinstall.test_core')


class EnqueueDeployedCoreTestCase(unittest.TestCase):

    """ Tests core.enqueue_deployed_charms() to make sure waiting
    for services to start are handled properly.
    """

    def setUp(self):
        self.conf = Config({})
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

    def test_validate_services_ready(self):
        """ Verifies services ready allow enqueue to complete
        to end of its routine """
        self.conf.setopt('headless', False)
        dc = Controller(
            ui=self.mock_ui, config=self.conf,
            loop=self.mock_loop)
        dc.initialize = MagicMock()
        dc.juju_state = JujuState(juju=MagicMock())
        dc.juju_state.all_agents_started = MagicMock()
        dc.juju_state.all_agents_started.return_value = all(
            self.services_ready)

        dc.enqueue_deployed_charms()
        self.mock_loop.redraw_screen.assert_called_once_with()

    def test_services_ready(self):
        """ Verifies all ready services  """
        juju_state = JujuState(juju=MagicMock())
        services = PropertyMock(return_value=self.services_ready)
        type(juju_state).services = services
        self.assertTrue(juju_state.all_agents_started())

    def test_some_services_ready(self):
        """ Verifies some ready services == not_ready list """
        juju_state = JujuState(juju=MagicMock())
        services = PropertyMock(return_value=self.services_some_ready)
        type(juju_state).services = services
        not_ready = [(a, b) for a, b in juju_state.get_agents_states()
                     if b != 'started']
        self.assertEqual(len(not_ready), 2)
