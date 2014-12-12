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
import sys
import json
import time
import shutil
from cloudinstall.config import Config
from cloudinstall.installbase import InstallBase
from cloudinstall import utils


log = logging.getLogger('cloudinstall.single_install')


class SingleInstallException(Exception):
    pass


class SingleInstall(InstallBase):

    def __init__(self, opts, display_controller):
        self.opts = opts
        super().__init__(display_controller)
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
        """ preps userdata file for container install
        """
        render_parts = {'extra_sshkeys': [utils.ssh_readkey()],
                        'extra_pkgs': ['juju-local']}
        if self.opts.extra_ppa:
            render_parts['extra_ppa'] = self.opts.extra_ppa
        dst_file = os.path.join(self.config.cfg_path,
                                'userdata.yaml')
        original_data = utils.load_template('userdata.yaml')
        log.debug("Userdata options: {}".format(render_parts))
        modified_data = original_data.render(render_parts)
        utils.spew(dst_file, modified_data)

    def prep_juju(self):
        """ preps juju environments for bootstrap
        """
        # configure juju environment for bootstrap
        single_env = utils.load_template('juju-env/single.yaml')
        single_env_modified = single_env.render(
            openstack_password=self.config.openstack_password)
        utils.spew(os.path.join(self.config.juju_path,
                                'environments.yaml'),
                   single_env_modified)

    def create_container_and_wait(self):
        """ Creates container and waits for cloud-init to finish
        """
        self.start_task("Creating container")
        utils.container_create(self.container_name, self.userdata)

        # Set autostart bit
        with open(os.path.join(self.container_abspath, 'config'), 'a+') as f:
            f.write("lxc.start.auto = 1\nlxc.start.delay = 5\n")

        # Mount points
        with open(os.path.join(self.container_abspath, 'fstab'), 'a+') as f:
            f.write(
                "{0} {1} none bind,create=dir\n".format(
                    self.config.cfg_path,
                    'home/ubuntu/.cloud-install'))
            f.write(
                "{0} {1} none bind,create=dir\n".format(
                    self.config.juju_path,
                    'home/ubuntu/.juju'))
            f.write(
                "{0} {1} none bind,create=dir\n".format(
                    os.path.join(utils.install_home(), '.ssh'),
                    'home/ubuntu/.ssh'))

        utils.container_start(self.container_name)
        utils.container_wait(self.container_name)

        tries = 1
        while not self.cloud_init_finished():
            time.sleep(1)
            tries = tries + 1

    def cloud_init_finished(self):
        """checks cloud-init result.json in container to find out status

        returns True if cloud-init finished with no errors, False if
        it's not done yet, and raises an exception if it had errors.
        """
        cmd = 'sudo cat /run/cloud-init/result.json'
        try:
            result_json = utils.container_run(self.container_name, cmd)
            # convert from bytes for json to process
            result_json = result_json.decode("utf-8")
            log.debug(result_json)
        except:
            log.debug("Waiting for cloud-init status result")
            return False

        if result_json == '':
            return False

        ret = json.loads(result_json)
        errors = ret['v1']['errors']
        if len(errors):
            log.error("Container cloud-init finished with "
                      "errors: {}".format(errors))
            # FIXME: Log errors for now, don't be fatal as the main
            # error is coming from a pollinate command unable
            # to run which doesn't seem to effect the installer.
            # raise Exception("Container cloud-init returned errors")
        return True

    def _install_upstream_deb(self):
        log.debug('Found upstream deb, installing that instead')
        filename = os.path.basename(self.opts.upstream_deb)
        utils.container_run(
            self.container_name, 'sudo dpkg -i .cloud-install/{}'.format(
                filename))

    def set_perms(self):
        """ sets permissions
        """
        try:
            utils.chown(self.config.cfg_path,
                        utils.install_user(),
                        utils.install_user(),
                        recursive=True)
            utils.get_command_output("sudo chmod 700 {}".format(
                self.config.cfg_path))
            utils.get_command_output("sudo chmod 600 -R {}/*".format(
                self.config.cfg_path))
        except:
            raise SingleInstallException(
                "Unable to set ownership for {}".format(self.config.cfg_path))

    def run(self):
        self.register_tasks([
            "Initializing Environment",
            "Creating container",
            "Bootstrapping Juju"])

        self.start_task("Initializing Environment")
        self.do_install_async()

    @utils.async
    def do_install_async(self):
        self.do_install()

    def do_install(self):
        self.display_controller.info_message("Building environment")
        if os.path.exists(self.container_abspath):
            # Container exists, handle return code in installer
            raise Exception("Container exists, please uninstall or kill "
                            "existing cloud before proceeding.")

        utils.ssh_genkey()

        # Preparations
        self.prep_userdata()

        # setup charm configurations
        utils.render_charm_config(self.config, self.opts)

        self.prep_juju()

        # Set permissions
        self.set_perms()

        # Start container
        self.create_container_and_wait()

        # Install local copy of openstack installer if provided
        if self.opts.upstream_deb and os.path.isfile(self.opts.upstream_deb):
            shutil.copy(self.opts.upstream_deb, self.config.cfg_path)
            self._install_upstream_deb()

        # start the party
        cloud_status_bin = ['openstack-status']
        self.display_controller.info_message("Bootstrapping Juju")
        self.start_task("Bootstrapping Juju")
        utils.container_run(self.container_name, "juju bootstrap")
        utils.container_run(self.container_name, "juju status")

        if self.opts.install_only:
            log.info("Done installing, stopping here per --install-only.")
            sys.exit(0)

        self.display_controller.info_message("Starting cloud deployment")
        utils.container_run_status(
            self.container_name, " ".join(cloud_status_bin))
