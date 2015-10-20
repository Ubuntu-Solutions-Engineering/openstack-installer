# Copyright 2014, 2015 Canonical, Ltd.
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

from .multi import (MultiInstall,
                    MultiInstallExistingMaas)


log = logging.getLogger('cloudinstall.c.i.landscape')


class LandscapeInstall:

    def __init__(self, loop, display_controller, config):
        self.config = config
        self.display_controller = display_controller
        self.loop = loop
        self.config.setopt('install_type', 'OpenStack Autopilot')

        self.landscape_tasks = ["Preparing Landscape",
                                "Deploying Landscape",
                                "Registering against Landscape"]

    def _do_install_existing_maas(self):
        """ Performs the landscape deployment with existing MAAS
        """
        if self.config.getopt('headless'):
            MultiInstall(self.loop, self.display_controller,
                         self.config, self.landscape_tasks).do_install()
        else:
            MultiInstallExistingMaas(
                self.loop, self.display_controller,
                self.config, post_tasks=self.landscape_tasks).run()

    def _save_lds_creds(self, creds):
        admin_name = creds['admin_name'].value
        admin_email = creds['admin_email'].value
        system_email = creds['admin_email'].value
        maas_server = creds['maas_server'].value
        maas_apikey = creds['maas_apikey'].value
        self.config.setopt('landscapecreds', dict(admin_name=admin_name,
                                                  admin_email=admin_email,
                                                  system_email=system_email))
        self.config.setopt('maascreds', dict(maas_server=maas_server,
                                             maas_apikey=maas_apikey))

        # Validate
        if not maas_server:
            self.display_controller.status_error_message(
                "Missing required MAAS Server")
            return self.run()

        if not maas_apikey:
            self.display_controller.status_error_message(
                "Missing required MAAS API Key")
            return self.run()

        log.debug("Existing MAAS defined, doing a LDS "
                  "installation with existing MAAS.")
        self.config.setopt('maascreds', dict(api_host=maas_server,
                                             api_key=maas_apikey))

        self._do_install_existing_maas()

    def run(self):
        if self.config.getopt('headless'):
            self._do_install_existing_maas()
        else:
            self.display_controller.status_info_message(
                "Please enter your Landscape information and "
                "MAAS Server IP and API Key. Use the MAAS web UI or "
                "'maas list' to find your API Key")
            self.display_controller.show_landscape_input(
                "OpenStack Autopilot Setup",
                self._save_lds_creds)
