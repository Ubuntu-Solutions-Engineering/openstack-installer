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
import os

from cloudinstall.config import (INSTALL_TYPE_SINGLE,
                                 INSTALL_TYPE_MULTI,
                                 INSTALL_TYPE_LANDSCAPE)
from cloudinstall.state import InstallState
from cloudinstall.alarms import AlarmMonitor
import cloudinstall.utils as utils
from cloudinstall.config import OPENSTACK_RELEASE_LABELS
from cloudinstall.controllers.install import (SingleInstall,
                                              LandscapeInstall,
                                              MultiInstallExistingMaas)


log = logging.getLogger('cloudinstall.install')


class InstallController:

    """ Install controller """

    # These are overriden in tests
    SingleInstall = SingleInstall
    MultiInstallExistingMaas = MultiInstallExistingMaas
    LandscapeInstall = LandscapeInstall

    def __init__(self, ui, config, loop):
        self.ui = ui
        self.config = config
        self.loop = loop
        self.install_type = None
        self.config.setopt('current_state', InstallState.RUNNING.value)
        if not self.config.getopt('headless'):
            rel = self.config.getopt('openstack_release')
            label = OPENSTACK_RELEASE_LABELS[rel]
            self.ui.set_openstack_rel(label)

    def _set_install_type(self, install_type):
        self.install_type = install_type
        self.ui.show_password_input(
            'Create a New OpenStack Password', self._save_password)

    def _save_password(self, creds):
        """ Checks passwords match and proceeds
        """
        password = creds['password'].value
        if password.isdigit():
            self.ui.status_error_message("Password must not be a number")
            return self.ui.show_password_input(
                'Create a New OpenStack Password', self._save_password)
        if 'confirm_password' in creds:
            confirm_password = creds['confirm_password'].value
        if password and password == confirm_password:
            self.config.setopt('openstack_password', password)
            self.do_install()
        else:
            self.ui.status_error_message('Passwords did not match')
            return self.ui.show_password_input(
                'Create a New OpenStack Password', self._save_password)

    def _save_maas_creds(self, creds):
        maas_server = creds['maas_server'].value
        maas_apikey = creds['maas_apikey'].value

        if maas_server and maas_apikey:
            if maas_server.startswith("http"):
                self.ui.status_error_message('Please enter the MAAS server\'s '
                                             'IP address only, not a full URL')
                return self.ui.show_maas_input("Enter MAAS IP and API Key",
                                               self._save_maas_creds)
            self.config.setopt('maascreds', dict(api_host=maas_server,
                                                 api_key=maas_apikey))
            log.info("Performing a Multi Install with existing MAAS")
            return self.MultiInstallExistingMaas(
                self.loop, self.ui, self.config).run()
        else:
            self.ui.status_error_message('Please enter the MAAS server\'s '
                                         'IP address and API key to proceed.')
            return self.ui.show_maas_input("Enter MAAS IP and API Key",
                                           self._save_maas_creds)

    def update(self, *args, **kwargs):
        "periodically check for display changes"
        if self.config.getopt('current_state') == InstallState.RUNNING:
            pass
        elif self.config.getopt('current_state') == InstallState.NODE_WAIT:
            self.ui.render_machine_wait_view(self.config)
            self.loop.redraw_screen()

        AlarmMonitor.add_alarm(self.loop.set_alarm_in(1, self.update),
                               "installcontroller-update")

    def do_install(self):
        """ Perform install
        """
        # Set installed placeholder
        utils.spew(os.path.join(
            self.config.cfg_path, 'installed'), 'auto-generated')
        if self.install_type == INSTALL_TYPE_SINGLE[0]:
            self.ui.status_info_message("Performing a Single Install")
            self.SingleInstall(
                self.loop, self.ui, self.config).run()
        elif self.install_type == INSTALL_TYPE_MULTI[0]:
            # TODO: Clean this up a bit more I dont like relying on
            # opts.headless but in a few places
            if self.config.getopt('headless'):
                self.ui.status_info_message(
                    "Performing a Multi install with existing MAAS")
                self.MultiInstallExistingMaas(
                    self.loop, self.ui, self.config).run()
            else:
                self.ui.show_maas_input(
                    "Enter MAAS IP and API Key",
                    self._save_maas_creds)
        elif self.install_type == INSTALL_TYPE_LANDSCAPE[0]:
            log.info("Performing a OpenStack Autopilot install")
            self.LandscapeInstall(
                self.loop, self.ui, self.config).run()
        else:
            os.remove(os.path.join(self.config.cfg_path, 'installed'))
            raise ValueError("Unknown install type: {}".format(
                self.install_type))

    def start(self):
        """ Start installer eventloop
        """
        if self.config.getopt('headless'):
            self.install_type = self.config.getopt('install_type')
            if not self.install_type:
                log.error('Fatal error: '
                          'Unable to read install type from configuration.')
                self.loop.exit(1)
            try:
                self.do_install()
            except:
                log.exception("Fatal error")
                self.loop.exit(1)

        else:
            self.ui.select_install_type(
                self.config.install_types(), self._set_install_type)

        self.update()
        self.loop.run()
