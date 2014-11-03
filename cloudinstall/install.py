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
import urwid

from cloudinstall.core import DisplayController
from cloudinstall.installbase import FakeInstall
from cloudinstall.single_install import SingleInstall
from cloudinstall.landscape_install import LandscapeInstall
from cloudinstall.multi_install import (MultiInstallNewMaas,
                                        MultiInstallExistingMaas)

log = logging.getLogger('cloudinstall.install')


class InstallController(DisplayController):

    """ Install controller """

    def __init__(self, **kwds):
        super().__init__(**kwds)

    def _save_password(self, creds):
        """ Checks passwords match and proceeds
        """
        password = creds['password'].value
        if 'confirm_password' in creds:
            confirm_password = creds['confirm_password'].value
        if password and \
           password == confirm_password:
            self.config.save_password(password)
            self.ui.hide_show_password_input()
            self.select_install_type()
        else:
            self.error_message('Passwords did not match, try again ..')
            return self.show_password_input(
                'Create a new Openstack Password', self._save_password)

    def select_install_type(self):
        """ Dialog for selecting installation type
        """
        self.info_message("Choose your installation path ..")
        self.show_selector_info('Install Type',
                                self.config.install_types,
                                self.do_install)

    def main_loop(self):
        if not hasattr(self, 'loop'):
            self.loop = urwid.MainLoop(self.ui,
                                       self.config.STYLES,
                                       handle_mouse=True,
                                       unhandled_input=self.header_hotkeys)

        self.info_message("Get started by entering an Openstack password "
                          "to use in your cloud ..")

        self.ui.show_password_input(
            'Create a new Openstack Password', self._save_password)
        self.loop.run()

    def do_install(self, install_type):
        """ Callback for install type selector
        """
        self.ui.hide_selector_info()
        if 'Single' in install_type:
            self.set_openstack_rel("Icehouse (2014.1.1)")
            SingleInstall(self.opts, self).run()
        elif 'Multi with existing MAAS' == install_type:
            self.set_openstack_rel("Icehouse (2014.1.1)")
            MultiInstallExistingMaas(self.opts, self).run()
        elif 'Multi' == install_type:
            self.set_openstack_rel("Icehouse (2014.1.1)")
            MultiInstallNewMaas(self.opts, self).run()
        else:
            self.set_openstack_rel("")
            LandscapeInstall(self.opts, self).run()
