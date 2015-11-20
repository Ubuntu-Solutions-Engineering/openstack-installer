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
import urwid
from unittest.mock import MagicMock, ANY
# FIXME: http://www.tornadoweb.org/en/stable/testing.html
# from tornado import testing
from cloudinstall.ev import EventLoop
from cloudinstall.config import Config
from cloudinstall.core import Controller
from tempfile import NamedTemporaryFile
log = logging.getLogger('cloudinstall.test_ev')


class EventLoopCoreTestCase(unittest.TestCase):

    def setUp(self):
        self._temp_conf = Config({}, save_backups=False)
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            # Override config file to save to
            self.conf = Config(self._temp_conf._config, tempf.name,
                               save_backups=False)
        self.mock_ui = MagicMock(name='ui')
        self.mock_log = MagicMock(name='log')
        self.mock_loop = MagicMock(name='loop')

    def make_ev(self, headless=False):
        self.conf.setopt('headless', headless)
        return EventLoop(self.mock_ui, self.conf,
                         self.mock_log)

    def test_validate_loop(self):
        """ Validate eventloop runs """
        self.conf.setopt('headless', False)
        self.conf.setopt('openstack_release', 'kilo')
        dc = Controller(
            ui=self.mock_ui, config=self.conf,
            loop=self.mock_loop)
        dc.initialize = MagicMock()
        dc.start()
        self.mock_loop.run.assert_called_once_with()

    # @testing.gen_test
    @unittest.skip
    def test_validate_redraw_screen_commit_placement(self):
        """ Validate redraw_screen on commit_placement """
        self.conf.setopt('headless', False)
        dc = Controller(
            ui=self.mock_ui, config=self.conf,
            loop=self.mock_loop)
        dc.initialize = MagicMock()
        dc.commit_placement()
        self.mock_loop.redraw_screen.assert_called_once_with()

    # @testing.gen_test
    @unittest.skip
    def test_validate_redraw_screen_enqueue(self):
        """ Validate redraw_screen on enqueue_deployed_charms """
        self.conf.setopt('headless', False)
        dc = Controller(
            ui=self.mock_ui, config=self.conf,
            loop=self.mock_loop)
        dc.initialize = MagicMock()
        dc.enqueue_deployed_charms()
        self.mock_loop.redraw_screen.assert_called_once_with()

    def test_validate_set_alarm_in(self):
        """ Validate set_alarm_in called with eventloop """
        dc = Controller(
            ui=self.mock_ui, config=self.conf,
            loop=self.mock_loop)
        dc.initialize = MagicMock()
        self.conf.node_install_wait_interval = 1
        dc.update(self.conf.node_install_wait_interval, ANY)
        self.mock_loop.set_alarm_in.assert_called_once_with(1, ANY)

    def test_validate_exit(self):
        """ Validate error code set with eventloop """
        ev = self.make_ev()
        dc = Controller(
            ui=self.mock_ui, config=self.conf,
            loop=ev)
        dc.initialize = MagicMock()
        with self.assertRaises(urwid.ExitMainLoop):
            dc.loop.exit(1)
        self.assertEqual(ev.error_code, 1)

    def test_hotkey_exit(self):
        ev = self.make_ev()
        dc = Controller(
            ui=self.mock_ui, config=self.conf,
            loop=ev)
        dc.initialize = MagicMock()
        with self.assertRaises(urwid.ExitMainLoop):
            dc.loop.header_hotkeys('q')
        self.assertEqual(ev.error_code, 0)

    def test_repr_ev(self):
        """ Prints appropriate class string for eventloop """
        ev = self.make_ev()
        dc = Controller(
            ui=self.mock_ui, config=self.conf,
            loop=ev)
        dc.initialize = MagicMock()
        self.assertEqual(str(ev), '<eventloop urwid based on tornado()>')

    def test_repr_no_ev(self):
        """ Prints appropriate class string for no eventloop """
        ev = self.make_ev(True)
        dc = Controller(
            ui=self.mock_ui, config=self.conf,
            loop=ev)
        dc.initialize = MagicMock()
        self.assertEqual(str(ev), '<eventloop disabled>')

    def test_validate_exit_no_ev(self):
        """ Validate SystemExit with no eventloop """
        ev = self.make_ev(True)
        dc = Controller(
            ui=self.mock_ui, config=self.conf,
            loop=ev)
        dc.initialize = MagicMock()
        with self.assertRaises(SystemExit) as cm:
            dc.loop.exit(1)
        exc = cm.exception
        self.assertEqual(ev.error_code, exc.code, "Found loop")
