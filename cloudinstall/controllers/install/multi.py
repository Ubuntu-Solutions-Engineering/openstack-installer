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
import os
import pwd
import re
import shlex
import socket
import time
import yaml

from subprocess import check_output
from tempfile import TemporaryDirectory

from cloudinstall.state import InstallState
from cloudinstall.netutils import get_ip_set

from cloudinstall import utils


log = logging.getLogger('cloudinstall.c.i.multi')


class MultiInstall:

    def __init__(self, loop, display_controller,
                 config, post_tasks=None):
        self.loop = loop
        self.config = config
        self.display_controller = display_controller
        self.tasker = self.display_controller.tasker(loop, config)
        self.tempdir = TemporaryDirectory(suffix="cloud-install")
        if post_tasks:
            self.post_tasks = post_tasks
        else:
            self.post_tasks = []
        self.installing_new_maas = False
        # Sets install type
        if not self.config.is_landscape():
            self.config.setopt('install_type', 'Multi')

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
                raise MaasInstallError(
                    "Unable to set ownership for {}".format(d))

    def do_install(self):
        self.tasker.start_task("Bootstrapping Juju")
        self.config.setopt('current_state', InstallState.RUNNING.value)

        maas_creds = self.config.getopt('maascreds')
        maas_env = utils.load_template('juju-env/maas.yaml')

        render_parts = {'openstack_password':
                        self.config.getopt('openstack_password'),
                        'maas_server': maas_creds['api_host'],
                        'maas_apikey': maas_creds['api_key'],
                        'ubuntu_series':
                        self.config.getopt('ubuntu_series')}

        for opt in ['http_proxy', 'https_proxy', 'no_proxy',
                    'image_metadata_url', 'tools_metadata_url']:
            val = self.config.getopt(opt)
            if val:
                render_parts[opt] = val

        maas_env_modified = maas_env.render(render_parts)

        check_output(['mkdir', '-p', self.config.juju_path()])
        utils.spew(self.config.juju_environments_path,
                   maas_env_modified)

        utils.render_charm_config(self.config)

        utils.ssh_genkey()

        # Set remaining permissions
        self.set_perms()

        # Starts the party
        self.display_controller.status_info_message("Bootstrapping Juju")

        dbgflags = ""
        if os.getenv("DEBUG_JUJU_BOOTSTRAP"):
            dbgflags = "--debug"

        bsflags = ""
        #    bsflags = " --constraints tags=physical"
        bstarget = os.getenv("JUJU_BOOTSTRAP_TO")
        if bstarget:
            bsflags += " --to {}".format(bstarget)

        cmd = ("{0} juju {1} bootstrap {2}".format(
            self.config.juju_home(), dbgflags, bsflags))

        log.debug("Bootstrapping Juju: {}".format(cmd))

        out = utils.get_command_output(cmd,
                                       timeout=None,
                                       user_sudo=True)
        if out['status'] != 0:
            log.debug("Problem during bootstrap: '{}'".format(out))
            raise Exception("Problem with juju bootstrap.")

        # workaround to avoid connection failure at beginning of
        # openstack-status
        out = utils.get_command_output(
            "{0} juju status".format(
                self.config.juju_home()),
            timeout=None,
            user_sudo=True)
        if out['status'] != 0:
            log.debug("failure to get initial juju status: '{}'".format(out))
            raise Exception("Problem with juju status poke.")

        self.add_bootstrap_to_no_proxy()

        self.tasker.stop_current_task()

        if self.config.getopt('install_only'):
            log.info("Done installing, stopping here per --install-only.")
            self.config.setopt('install_only', True)
            self.loop.exit(0)

        # Return control back to landscape_install if need be
        if not self.config.is_landscape():
            args = ['openstack-status']
            if self.config.getopt('edit_placement'):
                args.append('--edit-placement')

            self.drop_privileges()
            os.execvp('openstack-status', args)
        else:
            log.debug("Finished MAAS step, now deploying Landscape.")
            return LandscapeInstallFinal(self,
                                         self.display_controller,
                                         self.config,
                                         self.loop).run()

    def drop_privileges(self):
        if os.geteuid() != 0:
            return

        user_name = os.getenv("SUDO_USER")
        pwnam = pwd.getpwnam(user_name)
        os.initgroups(user_name, pwnam.pw_gid)
        os.setregid(pwnam.pw_gid, pwnam.pw_gid)
        os.setreuid(pwnam.pw_uid, pwnam.pw_uid)

    def add_bootstrap_to_no_proxy(self):
        """Finds bootstrap node IP and adds it to the current setting of
        no-proxy in the juju env.
        """
        out = utils.get_command_output(
            "{0} juju status".format(
                self.config.juju_home()),
            timeout=None,
            user_sudo=True)
        if out['status'] != 0:
            log.debug("error from status: {}".format(out))
            raise Exception("Problem with juju status.")
        try:
            status = yaml.load(out['output'])
            bootstrap_dns_name = status['machines']['0']['dns-name']
        except:
            log.exception("Error parsing yaml from juju status")
            raise Exception("Problem getting bootstrap machine DNS name")

        # first attempt to get directly, then use juju run:
        try:
            bootstrap_ip = socket.gethostbyname(bootstrap_dns_name)

        except socket.gaierror as e:
            log.error("Failed to get ip directly: {}".format(e))

            out = utils.get_command_output(
                "{} juju run --machine 0 "
                "'ip -o -4 address show dev juju-br0'".format(
                    self.config.juju_home()))
            if out['status'] != 0:
                log.error("Failed to get ip: {}".format(out))
                raise Exception("Failed to get IP of bootstrap node")
            regex = re.compile("inet\s+(\d+\.\d+\.\d+\.\d+)\/")
            match = re.search(regex, out['output'].rstrip())
            if match:
                bootstrap_ip = match.group(1)
                bootstrap_ip = get_ip_set("{}/24".format(bootstrap_ip))
            else:
                log.error("Failed to get ip: {}".format(out))
                raise Exception("Failed to get IP of bootstrap node")

        out = utils.get_command_output(
            "{} juju get-env no-proxy".format(self.config.juju_home()),
            timeout=None, user_sudo=True)
        if out['status'] != 0:
            log.debug("error from get-env: {}".format(out))
            raise Exception("Problem getting existing no-proxy setting")

        no_proxy = "{},{}".format(
            out['output'].rstrip(), bootstrap_ip)

        out = utils.get_command_output(
            "{} juju set-env no-proxy={}".format(self.config.juju_home(),
                                                 no_proxy),
            timeout=None, user_sudo=True)
        if out['status'] != 0:
            log.debug("error from set-env: {}".format(out))
            raise Exception("Problem setting no-proxy environment")


class MultiInstallExistingMaas(MultiInstall):

    def run(self):
        self.tasker.register_tasks(["Bootstrapping Juju"] +
                                   self.post_tasks)

        if not self.config.getopt('headless'):
            msg = "Waiting for sufficient resources in MAAS"
            self.display_controller.status_info_message(msg)
            self.display_controller.current_installer = self
            self.config.setopt('current_state', InstallState.NODE_WAIT.value)
            # return here and end thread. machine_wait_view will call
            # do_install back on new async thread
        else:
            self.do_install()


class MaasInstallError(Exception):

    "An error involving installing a new MAAS"


# TODO clean up the landscape installer classes
class LandscapeInstallFinal:

    """ Final phase of landscape install
    """
    BUNDLE_URL = ("https://api.jujucharms.com/charmstore/v4/"
                  "~landscape/bundle/landscape-dense-maas/archive/bundle.yaml")

    def __init__(self, multi_installer, display_controller,
                 config, loop):
        self.config = config
        self.loop = loop
        self.config.save()
        self.multi_installer = multi_installer
        self.display_controller = display_controller
        self.maas = None
        self.maas_state = None
        self.lscape_configure_bin = os.path.join(
            self.config.bin_path, 'configure-landscape')
        self.lscape_yaml_path = os.path.join(
            self.config.cfg_path, 'landscape-deployments.yaml')

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
                raise Exception(
                    "Unable to set ownership for {}".format(d))

    def run(self):
        """Finish the installation once the questionnaire is finished.
        """
        self.deploy_landscape()

    def deploy_landscape(self):
        self.multi_installer.tasker.start_task("Preparing Landscape")
        self.display_controller.status_info_message(
            "Running")
        # FIXME: not sure if deployer is failing to access the juju
        # environment but I get random connection refused when
        # running juju-deployer (adam.stokes)
        time.sleep(10)

        # Set remaining permissions
        self.set_perms()

        try:
            self.display_controller.status_info_message(
                "Downloading latest Landscape Autopilot bundle")
            utils.download_url(self.BUNDLE_URL, self.lscape_yaml_path)
        except Exception as e:
            log.exception(e)
            raise e

        self.multi_installer.tasker.start_task("Deploying Landscape")
        self.run_deployer()

        self.multi_installer.tasker.start_task("Registering against Landscape")
        hostname = self.run_configure_script()

        self.multi_installer.tasker.stop_current_task()
        self.display_controller.clear_status()

        msg = []
        msg.append("To continue with OpenStack installation visit:\n\n")
        msg.append("http://{0}/account/standalone/openstack ".format(hostname))
        msg.append("\n\nLandscape Login Credentials:\n")
        msg.append(" Email: {}\n".format(
            self.config.getopt('landscapecreds')['admin_email']))
        msg.append(
            " Password: {}".format(self.config.getopt('openstack_password')))
        self.display_controller.show_step_info(msg)

    def run_deployer(self):
        # Prep deployer template for landscape
        lscape_password = utils.random_password()
        password_re = re.compile(
            '(change-me)')
        lscape_env = utils.slurp(self.lscape_yaml_path)
        lscape_env_re = password_re.sub(
            lscape_password, str(lscape_env))
        lscape_env_modified = {'landscape-dense-maas': yaml.load(
            lscape_env_re)}
        utils.spew(self.lscape_yaml_path,
                   yaml.dump(lscape_env_modified))

        out = utils.get_command_output(
            "{0} juju-deployer -WdvL -w 180 -c {1} "
            "landscape-dense-maas".format(
                self.config.juju_home(),
                self.lscape_yaml_path),
            timeout=None,
            user_sudo=True)
        if out['status']:
            log.error("Problem deploying Landscape: {}".format(out))
            raise Exception("Error deploying Landscape.")

    def run_configure_script(self):
        "runs configure-landscape, returns output (LDS hostname)"

        ldscreds = self.config.getopt('landscapecreds')
        args = {"bin": self.lscape_configure_bin,
                "admin_email": shlex.quote(ldscreds['admin_email']),
                "admin_name": shlex.quote(ldscreds['admin_name']),
                "sys_email": shlex.quote(ldscreds['system_email']),
                "maas_host": shlex.quote(
                    self.config.getopt('maascreds')['api_host'])}

        cmd = ("{bin} --admin-email {admin_email} "
               "--admin-name {admin_name} "
               "--system-email {sys_email} "
               "--maas-host {maas_host}".format(**args))

        log.debug("Running landscape configure: {}".format(cmd))

        out = utils.get_command_output(cmd, timeout=None)

        if out['status']:
            log.error("Problem with configuring Landscape: {}.".format(out))
            raise Exception("Error configuring Landscape.")

        return out['output'].strip()
