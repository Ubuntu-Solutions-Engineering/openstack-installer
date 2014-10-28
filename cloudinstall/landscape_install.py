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
import os

from cloudinstall.config import Config
from cloudinstall.multi_install import (MultiInstallNewMaas,
                                        MultiInstallExistingMaas)
from cloudinstall import utils


log = logging.getLogger('cloudinstall.landscape_install')


class LandscapeInstall:

    def __init__(self, opts, display_controller):
        self.config = Config()
        self.opts = opts
        self.display_controller = display_controller
        self.lds_admin_name = None
        self.lds_admin_email = None
        self.lds_system_email = None
        self.maas_server = None
        self.maas_server_key = None
        # Sets install type
        utils.spew(os.path.join(self.config.cfg_path,
                                'landscape'),
                   'auto-generated')

    def _do_install_existing_maas(self):
        """ Performs the landscape deployment with existing MAAS
        """
        MultiInstallExistingMaas(
            self.opts, self.display_controller).run()

    def _do_install_new_maas(self):
        """ Prepare new maas environment for landscape
        """
        MultiInstallNewMaas(self.opts, self.display_controller).run()

    def _save_lds_creds(self, creds):
        admin_name = creds['admin_name'].value
        admin_email = creds['admin_email'].value
        system_email = creds['system_email'].value
        maas_server = creds['maas_server'].value
        maas_apikey = creds['maas_apikey'].value
        self.config.save_landscape_creds(
            admin_name, admin_email, system_email,
            maas_server, maas_apikey)

        self.display_controller.ui.hide_widget_on_top()
        self.display_controller.info_message("Running ..")
        if not self.maas_server:
            log.debug("No maas credentials entered, doing a new MAAS install")
            self._do_install_new_maas()
        else:
            log.debug("Existing MAAS defined, doing a LDS "
                      "installation with existing MAAS.")
            self.config.save_maas_creds(maas_server,
                                        maas_apikey)
            self._do_install_existing_maas()

    def run(self):
        self.display_controller.info_message(
            "Please enter your Landscape information and "
            "optionally an existing MAAS Server IP. If MAAS "
            "is not defined a new one will be created for you.")
        self.display_controller.show_landscape_input("Landscape Setup",
                                                     self._save_lds_creds)
