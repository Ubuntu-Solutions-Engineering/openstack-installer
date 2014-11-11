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
from cloudinstall.single_install import SingleInstall
from cloudinstall.landscape_install import LandscapeInstall
from cloudinstall.multi_install import (MultiInstallNewMaas,
                                        MultiInstallExistingMaas)

log = logging.getLogger('cloudinstall.install')


class InstallController(DisplayController):

    """ Install controller """

    SingleInstall = SingleInstall
    MultiInstallExistingMaas = MultiInstallExistingMaas
    MultiInstallNewMaas = MultiInstallNewMaas
    LandscapeInstall = LandscapeInstall

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

    def _save_maas_creds(self, creds):
        self.ui.hide_widget_on_top()
        maas_server = creds['maas_server'].value
        maas_apikey = creds['maas_apikey'].value

        if maas_server and maas_apikey:
            self.config.save_maas_creds(maas_server,
                                        maas_apikey)
            self.MultiInstallExistingMaas(self.opts, self).run()
        else:
            self.MultiInstallNewMaas(self.opts, self).run()

    def select_install_type(self):
        """ Dialog for selecting installation type
        """
        self.info_message("Choose your installation path ..")
        self.show_selector_info('Install Type',
                                self.config.install_types,
                                self.do_install)

    def select_maas_type(self):
        """ Perform multi install based on existing
        MAAS or if a new MAAS will be installed
        """
        self.info_message(
            "If a MAAS exists please enter the Server IP and your "
            "administrator's API Key. Otherwise leave blank and a new "
            "MAAS will be created for you.")
        self.show_maas_input("MAAS Setup",
                             self._save_maas_creds)

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
        if install_type == "Single":
            self.set_openstack_rel("Icehouse (2014.1.3)")
            self.SingleInstall(self.opts, self).run()
        elif install_type == "Multi":
            self.set_openstack_rel("Icehouse (2014.1.3)")
            self.select_maas_type()
        elif install_type == "Landscape":
            self.set_openstack_rel("")
            self.LandscapeInstall(self.opts, self).run()
        else:
            raise ValueError("Unknown install type: {}".format(install_type))
