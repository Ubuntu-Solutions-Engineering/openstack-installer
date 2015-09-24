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
from unittest.mock import MagicMock, patch

from cloudinstall.config import Config
from cloudinstall.core import Controller
from cloudinstall.juju import JujuState

log = logging.getLogger('cloudinstall.test_core')


class WaitForDeployedServicesReadyCoreTestCase(unittest.TestCase):

    """ Tests core.wait_for_deployed_services_ready to make sure waiting
    for services to start are handled properly.
    """

    def setUp(self):
        self.conf = Config({}, save_backups=False)
        self.mock_ui = MagicMock(name='ui')
        self.mock_log = MagicMock(name='log')
        self.mock_loop = MagicMock(name='loop')

        self.conf.setopt('headless', False)
        self.dc = Controller(
            ui=self.mock_ui, config=self.conf,
            loop=self.mock_loop)
        self.dc.initialize = MagicMock()
        self.dc.juju_state = JujuState(juju=MagicMock())
        self.dc.juju_state.all_agents_started = MagicMock()

    def test_validate_services_ready(self):
        """ Verifies wait_for_deployed_services_ready

        time.sleep should not be called here as all services
        are in a started state.
        """
        self.dc.juju_state.all_agents_started.return_value = True

        with patch('cloudinstall.core.time.sleep') as mock_sleep:
            self.dc.wait_for_deployed_services_ready()
        self.assertEqual(len(mock_sleep.mock_calls), 0)

    def test_validate_services_some_ready(self):
        """ Verifies wait_for_deployed_services_ready against some of the
        services in started state

        Here we test if time.sleep was called twice due to some services
        being in an installing and allocating state.
        """
        self.dc.juju_state.all_agents_started.side_effect = [
            False, False, True, True]

        with patch('cloudinstall.core.time.sleep') as mock_sleep:
            self.dc.wait_for_deployed_services_ready()
        print(mock_sleep.mock_calls)
        self.assertEqual(len(mock_sleep.mock_calls), 2)
