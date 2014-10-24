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
import os
import sys
import time
from cloudinstall.config import Config
from cloudinstall.core import DisplayController
from cloudinstall import utils


log = logging.getLogger('cloudinstall.install')


class InstallException(Exception):
    pass


class SingleInstall:

    def __init__(self, opts, ui):
        self.opts = opts
        self.ui = ui
        self.config = Config()
        self.container_name = 'uoi-bootstrap'
        self.container_path = '/var/lib/lxc'
        self.container_abspath = os.path.join(self.container_path,
                                              self.container_name)
        self.userdata = os.path.join(
            self.config.cfg_path, 'userdata.yaml')

        # Sets install type
        utils.spew(os.path.join(self.config.cfg_path, 'single'),
                   'auto-generated')

    def prep_userdata(self):
        """ preps userdata file for container install """
        dst_file = os.path.join(self.config.cfg_path,
                                'userdata.yaml')
        original_data = utils.load_template('userdata.yaml')
        modified_data = original_data.render(
            extra_sshkeys=[utils.ssh_readkey()],
            extra_pkgs=['juju-local'])
        utils.spew(dst_file, modified_data)

    def create_container_and_wait(self):
        """ Creates container and waits for cloud-init to finish
        """
        utils.container_create(self.container_name, self.userdata)
        utils.container_start(self.container_name)
        utils.container_wait(self.container_name)
        tries = 1
        while not self.cloud_init_finished():
            self.ui.info_message("[{0}] * Waiting for container to finalize, "
                                 "please wait ...       ".format(tries))
            time.sleep(1)
            tries = tries + 1

    def cloud_init_finished(self):
        """ checks the log to see if cloud-init finished
        """
        log_file = os.path.join(self.container_abspath,
                                'rootfs/var/log/cloud-init-output.log')
        out = utils.get_command_output('sudo tail -n1 {0}'.format(log_file))
        if 'finished at' in out['output']:
            return True
        return False

    def copy_installdata_and_set_perms(self):
        """ copies install data and sets permissions on files/dirs
        """
        utils.get_command_output("chown {0}:{0} -R {1}".format(
            utils.install_user(), self.config.cfg_path))

        # copy over the rest of our installation data from host
        # and setup permissions

        utils.container_run(self.container_name, 'mkdir -p ~/.cloud-install')
        utils.container_run(
            self.container_name, 'sudo mkdir -p /etc/openstack')

        utils.container_cp(self.container_name,
                           os.path.join(
                               utils.install_home(), '.cloud-install/*'),
                           '.cloud-install/.')

        # our ssh keys too
        utils.container_cp(self.container_name,
                           os.path.join(utils.install_home(),
                                        '.ssh/id_rsa*'),
                           '.ssh/.')
        utils.container_run(self.container_name, "chmod 600 .ssh/id_rsa*")

    def run(self):
        if os.path.exists(self.container_abspath):
            # Container exists, handle return code in installer
            raise SystemExit("Container exists, please uninstall or kill "
                             "existing cloud before proceeding.")

        self.ui.info_message(
            "* Please wait while we generate your isolated environment ...")

        utils.ssh_genkey()

        # Prepare cloud-init file for creation
        self.prep_userdata()

        # Start container
        self.create_container_and_wait()

        # configure juju environment for bootstrap
        single_env = utils.load_template('juju-env/single.yaml')
        single_env_modified = single_env.render(
            openstack_password=self.config.openstack_password)
        utils.spew('/tmp/single.yaml', single_env_modified)
        utils.container_run(self.container_name,
                            'mkdir -p .juju')
        utils.container_cp(self.container_name,
                           '/tmp/single.yaml',
                           '.juju/environments.yaml')

        # Set permissions
        self.copy_installdata_and_set_perms()

        # setup charm confingurations
        charm_conf = utils.load_template('charmconf.yaml')
        charm_conf_modified = charm_conf.render(
            openstack_password=self.config.openstack_password)
        utils.spew(os.path.join(self.config.cfg_path,
                                'charmconf.yaml'),
                   charm_conf_modified)

        # start the party
        cloud_status_bin = ['cloud-status']
        if self.opts.enable_swift:
            cloud_status_bin.append('--enable-swift')
        self.ui.info_message("Bootstrapping Juju ..")
        utils.container_run(self.container_name, "juju bootstrap")
        utils.container_run(self.container_name, "juju status")
        self.ui.info_message("Starting cloud deployment ..")
        utils.container_run_status(
            self.container_name, " ".join(cloud_status_bin))


class MultiInstall:

    def __init__(self, opts, ui):
        self.opts = opts
        self.ui = ui
        self.config = Config()

        # Sets install type
        utils.spew(os.path.join(self.config.cfg_path, 'multi'),
                   'auto-generated')

    def set_perms(self):
        # Set permissions
        dirs = [self.config.cfg_path,
                os.path.join(utils.install_home(), '.juju')]
        for d in dirs:
            utils.get_command_output("chown {0}:{0} -R {1}".format(
                utils.install_user(), d))

    def do_install(self):
        maas_creds = self.config.maas_creds
        maas_env = utils.load_template('juju-env/maas.yaml')
        maas_env_modified = maas_env.render(
            maas_server=maas_creds['api_url'],
            maas_apikey=maas_creds['api_key'],
            openstack_password=self.config.openstack_password)
        utils.spew(self.config.juju_environments_path,
                   maas_env_modified)
        utils.ssh_genkey()

        # Set remaining permissions
        self.set_perms()

        # Starts the party
        out = utils.get_command_output("juju bootstrap",
                                       user_sudo=True)
        if not out['status']:
            cmd = ['cloud-status']
            if self.opts.enable_swift:
                cmd.append('--enable-swift')
            out = utils.get_command_output(" ".join(cmd),
                                           user_sudo=True)
            sys.exit(out['status'])
        else:
            raise SystemExit("Problem with juju bootstrap.")


class MultiInstallNewMaas(MultiInstall):

    def _save_maas_creds(self, maas_server, maas_apikey):
        self.config.save_maas_creds(maas_server, maas_apikey)

        # Saved maas creds, start the show
        self.do_install()

    def run(self):
        # Handle MAAS VM Install here.
        # Then prompt for maas credentials and server IP
        # continue with the install as normal
        self.ui.info_message("Please enter your MAAS Server IP "
                             "and your administrators API Key")
        self.ui.show_maas_input(self._save_maas_creds)


class MultiInstallExistingMaas(MultiInstall):

    def _save_maas_creds(self, maas_server, maas_apikey):
        self.config.save_maas_creds(maas_server, maas_apikey)

        # Saved maas creds, start the show
        self.do_install()

    def run(self):
        self.ui.info_message("Please enter your MAAS Server IP "
                             "and your administrators API Key")
        self.ui.show_maas_input(self._save_maas_creds)


class LandscapeInstall:

    def __init__(self, opts, ui):
        self.config = Config()
        self.opts = opts
        self.ui = ui
        self.lds_admin_name = None
        self.lds_admin_email = None
        self.lds_system_email = None
        self.maas_server = None
        self.maas_server_key = None
        self.lscape_configure_bin = os.path.join(
            self.config.bin_path, 'configure-landscape')
        self.lscape_yaml_path = os.path.join(
            self.config.cfg_path, 'landscape-deployments.yaml')

    def set_perms(self):
        # Set permissions
        dirs = [self.config.cfg_path,
                os.path.join(utils.install_home(), '.juju')]
        for d in dirs:
            utils.get_command_output("chown {0}:{0} -R {1}".format(
                utils.install_user(), d))

    def _do_install_existing_maas(self):
        """ Performs the landscape deployment with existing MAAS
        """
        pass
        MultiInstallExistingMaas(self.opts, self).run()

    def _do_install_new_maas(self):
        """ Prepare new maas environment for landscape
        """
        pass
        MultiInstallNewMaas(self.opts, self).run()

    def _save_lds_creds(self, admin_name, admin_email, system_email,
                        maas_server=None, maas_server_key=None):
        self.lds_admin_name = admin_name
        self.lds_admin_email = admin_email
        self.lds_system_email = system_email
        self.maas_server = maas_server
        self.maas_server_key = maas_server_key

        if not self.maas_server:
            self._do_install_new_maas()
        else:
            self.opts.with_maas_address = self.maas_server
            self.opts.with_maas_apikey = self.maas_server_key
            self._do_install_existing_maas()

    def run(self):
        self.ui.info_message("Please enter your Landscape information and "
                             "optionally an existing MAAS Server IP")
        self.ui.show_landscape_input(self._save_lds_creds)

        utils.ssh_genkey()

        # Prep deployer template for landscape
        lscape_password = utils.random_password()
        lscape_env = utils.load_template('landscape-deployments.yaml')
        lscape_env_modified = lscape_env.render(
            landscape_password=lscape_password.strip())
        utils.spew(self.lscape_yaml_path,
                   lscape_env_modified)

    def finalize_deploy(self):
        """ Finish installation once questionarre is finished.
        """

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
                                           admin_email="",
                                           name="",
                                           sys_email="",
                                           maas_host=""))
        if out['status']:
            raise SystemExit("Problem with configuring Landscape: {}.".format(
                out['output']))


class InstallController(DisplayController):

    """ Install controller """

    def __init__(self, **kwds):
        super().__init__(**kwds)

    def _save_password(self, password=None, confirm_pass=None):
        """ Checks passwords match and proceeds
        """
        if password and password == confirm_pass:
            self.config.save_password(password)
            self.ui.hide_show_password_input()
            self.select_install_type()
        else:
            self.error_message('Passwords did not match, try again ..')
            return self.show_password_input(
                'Openstack Password', self._save_password)

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
            'Openstack Password', self._save_password)
        self.loop.run()

    def do_install(self, install_type):
        """ Callback for install type selector
        """
        self.ui.hide_selector_info()
        if 'Single' in install_type:
            SingleInstall(self.opts, self).run()
        elif 'Multi with existing MAAS' == install_type:
            MultiInstallExistingMaas(self.opts, self).run()
        elif 'Multi' == install_type:
            MultiInstallNewMaas(self.opts, self).run()
        else:
            LandscapeInstall(self.opts, self).run()
