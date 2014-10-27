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
        self.lscape_configure_bin = os.path.join(
            self.config.bin_path, 'configure-landscape')
        self.lscape_yaml_path = os.path.join(
            self.config.cfg_path, 'landscape-deployments.yaml')

        # Sets install type
        utils.spew(os.path.join(self.config.cfg_path,
                                'landscape'),
                   'auto-generated')

    def set_perms(self):
        # Set permissions
        dirs = [self.config.cfg_path,
                os.path.join(utils.install_home(), '.juju')]
        for d in dirs:
            try:
                utils.chown(d,
                            utils.install_user(),
                            utils.install_user(),
                            recursive=True)
            except:
                raise SystemExit(
                    "Unable to set ownership for {}".format(d))

    def _do_install_existing_maas(self):
        """ Performs the landscape deployment with existing MAAS
        """
        MultiInstallExistingMaas(self.opts, self.display_controller).run()
        self.finalize_deploy()

    def _do_install_new_maas(self):
        """ Prepare new maas environment for landscape
        """
        MultiInstallNewMaas(self.opts, self.display_controller).run()
        self.finalize_deploy()

    def _save_lds_creds(self, admin_name, admin_email, system_email,
                        maas_server=None, maas_server_key=None):
        self.lds_admin_name = admin_name.value
        self.lds_admin_email = admin_email.value
        self.lds_system_email = system_email.value
        self.maas_server = maas_server.value
        self.maas_server_key = maas_server_key.value

        self.display_controller.ui.hide_widget_on_top()
        self.display_controller.info_message("Running ..")
        if not self.maas_server:
            self._do_install_new_maas()
        else:
            self.config.save_maas_creds(self.maas_server,
                                        self.maas_server_key)
            self._do_install_existing_maas()

    def run(self):
        self.display_controller.info_message(
            "Please enter your Landscape information and "
            "optionally an existing MAAS Server IP")
        self.display_controller.show_landscape_input("Landscape Setup",
                                                     self._save_lds_creds)

    def finalize_deploy(self):
        """ Finish installation once questionarre is finished.
        """
        utils.apt_install('openstack-landscape')

        # Prep deployer template for landscape
        lscape_password = utils.random_password()
        lscape_env = utils.load_template('landscape-deployments.yaml')
        lscape_env_modified = lscape_env.render(
            landscape_password=lscape_password.strip())
        utils.spew(self.lscape_yaml_path,
                   lscape_env_modified)

        # Set remaining permissions
        self.set_perms()

        # Juju deployer
        out = utils.get_command_output("juju-deployer -Wdv -c {0} "
                                       "landscape-dense-maas".format(
                                           self.lscape_yaml_path))
        if out['status']:
            raise SystemExit("Problem deploying Landscape: {}".format(
                out['status']))

        # Configure landscape
        out = utils.get_command_output("{bin} --admin-email={admin_email} "
                                       "--admin-name={name} "
                                       "--system-email={sys_email} "
                                       "--maas-host={maas_host}".format(
                                           self.lscape_configure_bin,
                                           admin_email=self.lds_admin_email,
                                           name=self.lds_admin_name,
                                           sys_email=self.lds_system_email,
                                           maas_host=self.maas_server))
        if out['status']:
            raise SystemExit("Problem with configuring Landscape: {}.".format(
                out['output']))
