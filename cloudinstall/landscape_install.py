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

from cloudinstall.multi_install import (MultiInstallNewMaas,
                                        MultiInstallExistingMaas)


log = logging.getLogger('cloudinstall.landscape_install')


class LandscapeInstall:

    def __init__(self, opts, display_controller, config, loop):
        self.config = config
        self.opts = opts
        self.loop = loop
        self.display_controller = display_controller
        self.config.set_install_type('landscape')

        self.landscape_tasks = ["Preparing Landscape",
                                "Deploying Landscape",
                                "Registering against Landscape"]

    def _do_install_existing_maas(self):
        """ Performs the landscape deployment with existing MAAS
        """
        MultiInstallExistingMaas(
            self.opts, self.loop, self.display_controller,
            post_tasks=self.landscape_tasks,
            config=self.config).run()

    def _do_install_new_maas(self):
        """ Prepare new maas environment for landscape
        """
        MultiInstallNewMaas(self.opts, self.loop, self.display_controller,
                            post_tasks=self.landscape_tasks,
                            config=self.config).run()

    def _save_lds_creds(self, creds):
        admin_name = creds['admin_name'].value
        admin_email = creds['admin_email'].value
        system_email = creds['admin_email'].value
        maas_server = creds['maas_server'].value
        maas_apikey = creds['maas_apikey'].value
        self.config.save_landscape_creds(
            admin_name, admin_email, system_email,
            maas_server, maas_apikey)

        self.display_controller.ui.hide_widget_on_top()

        # Validate
        if not maas_server:
            log.debug("No MAAS server entered.")
            self.display_controller.flash("Missing required MAAS Server")
            return self.run()

        if not maas_apikey:
            log.debug("No MAAS api key entered.")
            self.display_controller.flash("Missing required MAAS API Key")
            return self.run()

        # self.display_controller.flash_reset()
        log.debug("Existing MAAS defined, doing a LDS "
                  "installation with existing MAAS.")
        self.config.save_maas_creds(maas_server,
                                    maas_apikey)
        self._do_install_existing_maas()

    def run(self):
        self.display_controller.info_message(
            "Please enter your Landscape information and "
            "MAAS Server IP and API Key. Use the MAAS web UI or 'maas list' "
            "to find your API Key")
        self.display_controller.show_landscape_input(
            "Landscape OpenStack Autopilot Setup",
            self._save_lds_creds)
