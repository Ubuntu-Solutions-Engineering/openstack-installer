#!/usr/bin/env python
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

import logging
import unittest
from unittest.mock import MagicMock, patch
from cloudinstall.state import InstallState, ControllerState
from cloudinstall.config import Config
from tempfile import NamedTemporaryFile

log = logging.getLogger('cloudinstall.test_state')


class InstallStateTestCase(unittest.TestCase):

    def setUp(self):
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self.conf = Config({}, tempf.name)

        self.bad_states_int = [5, 6, 7]
        self.good_states_int = [0, 1]

    def test_install_state(self):
        """ Validate config install state """

        for i in self.bad_states_int:
            self.conf.setopt('current_state', i)
            with self.assertRaises(ValueError):
                s = self.conf.getopt('current_state')
                InstallState(s)

        for i in self.good_states_int:
            self.conf.setopt('current_state', i)
            s = self.conf.getopt('current_state')
            self.assertEqual(InstallState(s), i)


class ControllerStateTestCase(unittest.TestCase):

    def setUp(self):
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self.conf = Config({}, tempf.name)

        self.bad_states_int = [5, 6, 7]
        self.good_states_int = [0, 1, 2]

    def test_set_controller_state(self):
        """ Validate config controller state """

        for i in self.bad_states_int:
            self.conf.setopt('current_state', i)
            with self.assertRaises(ValueError):
                s = self.conf.getopt('current_state')
                ControllerState(s)

        for i in self.good_states_int:
            self.conf.setopt('current_state', i)
            s = self.conf.getopt('current_state')
            self.assertEqual(ControllerState(s), i)


class MultiInstallStateTestCase(unittest.TestCase):

    """ Handles validating current state within a
    multi install
    """

    def setUp(self):
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self.conf = Config({}, tempf.name)
        self.mock_ui = MagicMock(name='ui')

    @patch('cloudinstall.multi_install.MultiInstall')
    def test_do_install_sets_state(self, MultiInstall):
        """ Validate installstate in multi install """
        mi = MultiInstall(self.mock_ui, config=self.conf)
        mi.do_install()
        self.assertEqual(
            self.conf.getopt('current_state'), InstallState.RUNNING)


class CoreStateTestCase(unittest.TestCase):

    """ Handles validating current state within the controllers
    core
    """

    def setUp(self):
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self.conf = Config({}, tempf.name)
        self.mock_ui = MagicMock(name='ui')

    @patch('cloudinstall.core.Controller')
    def test_controller_state_init(self, Controller):
        """ Validate controller state in core during class init """
        Controller(self.mock_ui, self.conf)
        self.assertEqual(
            self.conf.getopt('current_state'), ControllerState.INSTALL_WAIT)
