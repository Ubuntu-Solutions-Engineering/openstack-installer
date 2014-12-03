#!/usr/bin/env python
#
# tests the ui module
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
from unittest.mock import MagicMock

from cloudinstall.ui import Selector

log = logging.getLogger('cloudinstall.test_ui')


class SelectorTestCase(unittest.TestCase):

    def test_selector_submit_sends_text(self):
        mock_cb = MagicMock()
        s = Selector("title", ["opt1", "opt2"], mock_cb)
        s.submit(MagicMock(name="the button arg is unused"))
        log.debug("self.input_items: {}".format(s.input_items))
        mock_cb.assert_called_with("opt1")
