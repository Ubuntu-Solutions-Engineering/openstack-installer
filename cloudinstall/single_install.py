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
import json
import time
import shutil
from cloudinstall import utils


log = logging.getLogger('cloudinstall.single_install')


class SingleInstallException(Exception):
    pass


class SingleInstall:

    def __init__(self, loop, display_controller, config):
        self.display_controller = display_controller
        self.config = config
        self.loop = loop
        self.tasker = self.display_controller.tasker(loop, config)
        self.container_name = 'uoi-bootstrap'
        self.container_path = '/var/lib/lxc'
        self.container_abspath = os.path.join(self.container_path,
                                              self.container_name)
        self.userdata = os.path.join(
            self.config.cfg_path, 'userdata.yaml')

        # Sets install type
        self.config.setopt('install_type', 'Single')

    def prep_userdata(self):
        """ preps userdata file for container install
        """
        render_parts = {'extra_sshkeys': [utils.ssh_readkey()]}

        if self.config.getopt('extra_ppa'):
            render_parts['extra_ppa'] = self.config.getopt('extra_ppa')

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
            openstack_password=self.config.getopt('openstack_password'))
        utils.spew(os.path.join(self.config.juju_path(),
                                'environments.yaml'),
                   single_env_modified,
                   owner=utils.install_user())

    def create_container_and_wait(self):
        """ Creates container and waits for cloud-init to finish
        """
        self.tasker.start_task("Creating container")

        lxc_config_filename = os.path.join(self.config.cfg_path, 'lxc.config')
        with open(lxc_config_filename, 'w') as f:
            f.write("lxc.network.type = veth\n"
                    "lxc.network.link = lxcbr0\n"
                    # note we do not do "lxc.network.flags = up" on purpose.
                    # we will bring up the network later
                    "lxc.mount.auto = cgroup:mixed\n"
                    "lxc.start.auto = 1\n"
                    "lxc.start.delay = 5")

        utils.container_create(self.container_name, lxc_config_filename,
                               self.userdata)

        # Mount points
        with open(os.path.join(self.container_abspath, 'fstab'), 'a+') as f:
            f.write(
                "{0} {1} none bind,create=dir\n".format(
                    self.config.cfg_path,
                    'home/ubuntu/.cloud-install'))
            # TODO: Remove as its not needed since juju
            # resides in ~/.cloud-install
            # f.write(
            #     "{0} {1} none bind,create=dir\n".format(
            #         self.config.juju_path(),
            #         'home/ubuntu/.juju'))
            # FIXME: causing some issues with authorized_keys
            # having its permission changed and not allowing
            # ssh into the container without password.
            # f.write(
            #     "{0} {1} none bind,create=dir\n".format(
            #         os.path.join(utils.install_home(), '.ssh'),
            #         'home/ubuntu/.ssh'))
            f.write(
                "/var/cache/lxc var/cache/lxc none bind,create=dir\n")

        lxc_logfile = os.path.join(self.config.cfg_path, 'lxc.log')

        try:
            utils.container_start(self.container_name, lxc_logfile)
        except Exception as e:
            log.error(e)
            self.loop.exit(1)

        try:
            utils.container_wait_checked(self.container_name,
                                         lxc_logfile)
        except Exception as e:
            log.error(e)
            self.loop.exit(1)

        tries = 0
        while not self.cloud_init_finished(tries):
            time.sleep(1)
            tries += 1

        # we do this here instead of using cloud-init, for greater
        # control over ordering
        log.debug("Container started, cloud-init done.")

        log.debug("Editing lxc-net config to not manage lxcbr0 bridge inside "
                  "container")
        # write an empty lxc-net default so that the packaging does
        # not write its own when we install lxc
        utils.container_run(self.container_name, 'touch /etc/default/lxc-net')

        log.debug("Installing openstack & openstack-single directly, "
                  "and juju-local, libvirt-bin and lxc via deps")
        utils.container_run(self.container_name,
                            "env DEBIAN_FRONTEND=noninteractive apt-get -qy "
                            "-o Dpkg::Options::=--force-confdef "
                            "-o Dpkg::Options::=--force-confold "
                            "install openstack openstack-single")

        log.debug("Setting up lxcbr0 bridge config manually")
        utils.container_run(self.container_name, "ifdown eth0")
        utils.container_run(self.container_name,
                            "mv /etc/network/interfaces.d/eth0.cfg "
                            "/etc/network/interfaces.d/eth0.cfg.bak ")
        bridge_cfg_filename = os.path.join(self.container_abspath, 'rootfs',
                                           'etc', 'network', 'interfaces.d',
                                           'bridge.cfg')

        with open(bridge_cfg_filename, 'w') as f:
            f.write("auto eth0\n"
                    "    iface eth0 inet manual\n\n"
                    "auto lxcbr0\n"
                    "    iface lxcbr0 inet dhcp\n"
                    "    bridge_ports eth0\n")
        log.debug("bringing up network")
        utils.container_run(self.container_name, "ifup eth0 lxcbr0")

    def cloud_init_finished(self, tries, maxlenient=20):
        """checks cloud-init result.json in container to find out status

        For the first `maxlenient` tries, it treats a container with
        no IP and SSH errors as non-fatal, assuming initialization is
        still ongoing. Afterwards, will raise exceptions for those
        errors, so as not to loop forever.

        returns True if cloud-init finished with no errors, False if
        it's not done yet, and raises an exception if it had errors.

        """
        cmd = 'sudo cat /run/cloud-init/result.json'
        try:
            result_json = utils.container_run(self.container_name, cmd)
            log.debug(result_json)

        except utils.NoContainerIPException as e:
            log.debug("Container has no IPs according to lxc-info. "
                      "Will retry.")
            return False

        except utils.ContainerRunException as e:
            _, returncode = e.args
            if returncode == 255:
                if tries < maxlenient:
                    log.debug("Ignoring initial SSH error.")
                    return False
                raise e
            if returncode == 1:
                # the 'cat' did not find the file.
                log.debug("Waiting for cloud-init status result")
                return False
            else:
                log.debug("Unexpected return code from reading "
                          "cloud-init status in container.")
                raise e

        if result_json == '':
            return False

        ret = json.loads(result_json)
        errors = ret['v1']['errors']
        if len(errors):
            log.error("Container cloud-init finished with "
                      "errors: {}".format(errors))
            log.error("Top-level container OS did not initialize "
                      "correctly. See ~/.cloud-install/commands.log "
                      "for details.")
            self.loop.exit(1)
        return True

    def _install_upstream_deb(self):
        log.debug('Found upstream deb, installing that instead')
        filename = os.path.basename(self.config.getopt('upstream_deb'))
        utils.container_run(
            self.container_name,
            'sudo dpkg -i /home/ubuntu/.cloud-install/{}'.format(
                filename))

    def set_perms(self):
        """ sets permissions
        """
        try:
            log.info("Setting permissions for user {}".format(
                utils.install_user()))
            utils.chown(self.config.cfg_path,
                        utils.install_user(),
                        utils.install_user(),
                        recursive=True)
            utils.get_command_output("sudo chmod 700 {}".format(
                self.config.cfg_path))
            utils.get_command_output("sudo chmod 700 -R {}/*".format(
                self.config.cfg_path))
        except:
            log.error(
                "Unable to set ownership for {}".format(self.config.cfg_path))
            self.loop.exit(1)

    def run(self):
        self.tasker.register_tasks([
            "Initializing Environment",
            "Creating container",
            "Bootstrapping Juju"])

        self.tasker.start_task("Initializing Environment")
        if self.config.getopt('headless'):
            self.do_install()
        else:
            self.do_install_async()

    @utils.async
    def do_install_async(self):
        self.do_install()

    def do_install(self):
        self.display_controller.status_info_message("Building environment")
        if os.path.exists(self.container_abspath):
            # Container exists, handle return code in installer
            raise Exception("Container exists, please uninstall or kill "
                            "existing cloud before proceeding.")

        try:
            utils.ssh_genkey()
        except Exception as e:
            log.error(e)
            self.loop.exit(1)

        # Preparations
        self.prep_userdata()

        # setup charm configurations
        utils.render_charm_config(self.config)

        self.prep_juju()

        # Set permissions
        self.set_perms()

        # Start container
        self.create_container_and_wait()

        # Install local copy of openstack installer if provided
        upstream_deb = self.config.getopt('upstream_deb')
        if upstream_deb and os.path.isfile(upstream_deb):
            shutil.copy(upstream_deb, self.config.cfg_path)
            self._install_upstream_deb()

        # Stop before we attempt to access container
        if self.config.getopt('install_only'):
            log.info("Done installing, stopping here per --install-only.")
            self.config.setopt('install_only', True)
            self.loop.exit(0)

        # start the party
        cloud_status_bin = ['openstack-status']
        self.display_controller.status_info_message("Bootstrapping Juju")
        self.tasker.start_task("Bootstrapping Juju")
        utils.container_run(self.container_name,
                            "{0} juju bootstrap".format(
                                self.config.juju_home(True)),
                            use_ssh=True)
        utils.container_run(
            self.container_name,
            "{0} juju status".format(self.config.juju_home(True)),
            use_ssh=True)
        self.tasker.stop_current_task()

        self.display_controller.status_info_message(
            "Starting cloud deployment")
        utils.container_run_status(
            self.container_name, " ".join(cloud_status_bin), self.config)
