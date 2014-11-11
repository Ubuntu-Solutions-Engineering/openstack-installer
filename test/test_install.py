#!/usr/bin/env python
#
# tests install.py
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
from unittest.mock import patch


from cloudinstall.install import InstallController

log = logging.getLogger('cloudinstall.test_install')


class InstallControllerTestCase(unittest.TestCase):

    def setUp(self):
        class StubUI():

            release = None

            def hide_selector_info(self2):
                pass

            def hide_widget_on_top(self2):
                pass

            def status_info_message(self2, message):
                pass

            def show_maas_input(self2, *args):
                pass

            def status_openstack_rel(self2, text):
                self2.release = text

        ui = StubUI()
        self.controller = InstallController(ui=ui)

    @patch('cloudinstall.single_install.SingleInstall')
    def test_do_install_single_openstack_release(self, SingleInstall):
        """do_install will set the OpenStack release for Single"""
        self.controller.SingleInstall = SingleInstall
        self.controller.do_install("Single")
        self.assertEqual(self.controller.ui.release, "Icehouse (2014.1.3)")

    @patch('cloudinstall.multi_install.MultiInstallNewMaas')
    @patch('cloudinstall.multi_install.MultiInstallExistingMaas')
    def test_do_install_multi_openstack_release(
            self, MultiInstallNewMaas, MultiInstallExistingMaas):
        """do_install will set the OpenStack release for Multi"""
        self.controller.MultiInstallNewMaas = MultiInstallNewMaas
        self.controller.MultiInstallExistingMaas = MultiInstallExistingMaas
        self.controller.do_install("Multi")
        self.assertEqual(self.controller.ui.release, "Icehouse (2014.1.3)")

    @patch('cloudinstall.landscape_install.LandscapeInstall')
    def test_do_install_landscape_openstack_release(self, LandscapeInstall):
        """do_install will not set the OpenStack release for Landscape"""
        self.controller.LandscapeInstall = LandscapeInstall
        self.controller.do_install("Landscape")
        self.assertEqual(self.controller.ui.release, "")
