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

from ipaddress import IPv4Network
import logging
import os
import json
import time
import shutil
from cloudinstall import utils, netutils


log = logging.getLogger('cloudinstall.single_install')


class SingleInstallException(Exception):
    pass


class SingleInstall:

    def __init__(self, loop, display_controller, config):
        self.display_controller = display_controller
        self.config = config
        self.loop = loop
        self.tasker = self.display_controller.tasker(loop, config)
        username = utils.install_user()
        self.container_name = 'openstack-single-{}'.format(username)
        self.container_path = '/var/lib/lxc'
        self.container_abspath = os.path.join(self.container_path,
                                              self.container_name)
        self.userdata = os.path.join(
            self.config.cfg_path, 'userdata.yaml')

        # Sets install type
        self.config.setopt('install_type', 'Single')

    def _proxy_pollinate(self):
        """ Proxy pollinate if http/s proxy is set """
        # pass proxy through to pollinate
        http_proxy = self.config.getopt('http_proxy')
        https_proxy = self.config.getopt('https_proxy')
        log.debug('Found proxy info: {}/{}'.format(http_proxy, https_proxy))
        pollinate = ['env']
        if http_proxy:
            pollinate.append('http_proxy={}'.format(http_proxy))
        if https_proxy:
            pollinate.append('https_proxy={}'.format(https_proxy))
        pollinate.extend(['pollinate', '-q'])
        return pollinate

    def prep_userdata(self):
        """ preps userdata file for container install
        """
        render_parts = {'extra_sshkeys': [utils.ssh_readkey()]}

        if self.config.getopt('extra_ppa'):
            render_parts['extra_ppa'] = self.config.getopt('extra_ppa')

        render_parts['seed_command'] = self._proxy_pollinate()

        for opt in ['http_proxy', 'https_proxy', 'no_proxy',
                    'image_metadata_url', 'tools_metadata_url',
                    'apt_mirror']:
            val = self.config.getopt(opt)
            if val:
                render_parts[opt] = val

        dst_file = os.path.join(self.config.cfg_path,
                                'userdata.yaml')
        original_data = utils.load_template('userdata.yaml')
        log.info("Prepared userdata: {}".format(render_parts))
        modified_data = original_data.render(render_parts)
        utils.spew(dst_file, modified_data)

    def prep_juju(self):
        """ preps juju environments for bootstrap
        """
        render_parts = {'openstack_password':
                        self.config.getopt('openstack_password'),
                        'ubuntu_series':
                        self.config.getopt('ubuntu_series')}

        if self.config.getopt('http_proxy'):
            render_parts['http_proxy'] = self.config.getopt('http_proxy')

        if self.config.getopt('https_proxy'):
            render_parts['https_proxy'] = self.config.getopt('https_proxy')

        # configure juju environment for bootstrap
        single_env = utils.load_template('juju-env/single.yaml')
        single_env_modified = single_env.render(render_parts)
        utils.spew(os.path.join(self.config.juju_path(),
                                'environments.yaml'),
                   single_env_modified,
                   owner=utils.install_user())

    def write_lxc_net_config(self):
        """Finds and configures a new subnet for the host container,
        to avoid overlapping with IPs used for Neutron.
        """
        lxc_net_template = utils.load_template('lxc-net')
        lxc_net_container_filename = os.path.join(self.container_abspath,
                                                  'rootfs/etc/default/lxc-net')

        network = netutils.get_unique_lxc_network()
        self.config.setopt('lxc_network', network)

        nw = IPv4Network(network)
        addr = nw[1]
        netmask = nw.with_netmask.split('/')[-1]
        net_low, net_high = netutils.ip_range_max(nw, [addr])
        dhcp_range = "{},{}".format(net_low, net_high)
        render_parts = dict(addr=addr,
                            netmask=netmask,
                            network=network,
                            dhcp_range=dhcp_range)
        lxc_net = lxc_net_template.render(render_parts)
        name = self.container_name
        log.info("Writing lxc-net config for {}".format(name))
        utils.spew(lxc_net_container_filename, lxc_net)

        return network

    def add_static_route(self, lxc_net):
        """ Adds static route to host system
        """
        # Store container IP in config
        ip = utils.container_ip(self.container_name)
        self.config.setopt('container_ip', ip)

        log.info("Adding static route for {} via {}".format(lxc_net,
                                                            ip))

        out = utils.get_command_output(
            'ip route add {} via {} dev lxcbr0'.format(lxc_net, ip))
        if out['status'] != 0:
            raise Exception("Could not add static route for {}"
                            " network: {}".format(lxc_net, out['output']))

    def create_container_and_wait(self):
        """ Creates container and waits for cloud-init to finish
        """
        self.tasker.start_task("Creating Container")

        utils.container_create(self.container_name, self.userdata)

        with open(os.path.join(self.container_abspath, 'fstab'), 'w') as f:
            f.write("{0} {1} none bind,create=dir\n".format(
                self.config.cfg_path,
                'home/ubuntu/.cloud-install'))
            f.write("/var/cache/lxc var/cache/lxc none bind,create=dir\n")
            # Detect additional charm plugins and make available to the
            # container.
            charm_plugin_dir = self.config.getopt('charm_plugin_dir')
            if charm_plugin_dir \
               and self.config.cfg_path not in charm_plugin_dir:
                plug_dir = os.path.abspath(
                    self.config.getopt('charm_plugin_dir'))
                plug_base = os.path.basename(plug_dir)
                f.write("{d} home/ubuntu/{m} "
                        "none bind,create=dir\n".format(d=plug_dir,
                                                        m=plug_base))

            extra_mounts = os.getenv("EXTRA_BIND_DIRS", None)
            if extra_mounts:
                for d in extra_mounts.split(','):
                    mountpoint = os.path.basename(d)
                    f.write("{d} home/ubuntu/{m} "
                            "none bind,create=dir\n".format(d=d,
                                                            m=mountpoint))

        # update container config
        with open(os.path.join(self.container_abspath, 'config'), 'a') as f:
            f.write("lxc.mount.auto = cgroup:mixed\n"
                    "lxc.start.auto = 1\n"
                    "lxc.start.delay = 5\n"
                    "lxc.mount = {}/fstab\n".format(self.container_abspath))

        lxc_logfile = os.path.join(self.config.cfg_path, 'lxc.log')

        utils.container_start(self.container_name, lxc_logfile)

        utils.container_wait_checked(self.container_name,
                                     lxc_logfile)

        tries = 0
        while not self.cloud_init_finished(tries):
            time.sleep(1)
            tries += 1

        # we do this here instead of using cloud-init, for greater
        # control over ordering
        log.debug("Container started, cloud-init done.")

        lxc_network = self.write_lxc_net_config()
        self.add_static_route(lxc_network)

        self.tasker.start_task("Installing Dependencies")
        log.debug("Installing openstack & openstack-single directly, "
                  "and juju-local, libvirt-bin and lxc via deps")
        utils.container_run(self.container_name,
                            "env DEBIAN_FRONTEND=noninteractive apt-get -qy "
                            "-o Dpkg::Options::=--force-confdef "
                            "-o Dpkg::Options::=--force-confold "
                            "install openstack openstack-single")

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
                if tries < 1:
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
            raise Exception("Top-level container OS did not initialize "
                            "correctly.")
        return True

    def _install_upstream_deb(self):
        log.info('Found upstream deb, installing that instead')
        filename = os.path.basename(self.config.getopt('upstream_deb'))
        try:
            utils.container_run(
                self.container_name,
                'sudo dpkg -i /home/ubuntu/.cloud-install/{}'.format(
                    filename))
        except:
            # Make sure deps are installed if any new ones introduced by
            # the upstream packaging.
            utils.container_run(
                self.container_name, 'sudo apt-get install -qyf')

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
            utils.get_command_output("sudo chmod 777 {}".format(
                self.config.cfg_path))
            utils.get_command_output("sudo chmod 777 -R {}/*".format(
                self.config.cfg_path))
        except:
            msg = ("Error setting ownership for "
                   "{}".format(self.config.cfg_path))
            log.exception(msg)
            raise Exception(msg)

    def run(self):
        self.tasker.register_tasks([
            "Initializing Environment",
            "Creating Container",
            "Installing Dependencies",
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
            raise Exception("Container exists, please uninstall or kill "
                            "existing cloud before proceeding.")

        # check for deb early, will actually install it later
        upstream_deb = self.config.getopt('upstream_deb')
        if upstream_deb and not os.path.isfile(upstream_deb):
            raise Exception("Upstream deb '{}' "
                            "not found.".format(upstream_deb))

        utils.ssh_genkey()

        self.prep_userdata()

        utils.render_charm_config(self.config)

        self.prep_juju()

        self.set_perms()

        self.create_container_and_wait()

        # Copy over host ssh keys
        utils.container_cp(self.container_name,
                           os.path.join(utils.install_home(), '.ssh/id_rsa*'),
                           '.ssh/.')

        # Install local copy of openstack installer if provided
        if upstream_deb:
            shutil.copy(upstream_deb, self.config.cfg_path)
            self._install_upstream_deb()

        # Stop before we attempt to access container
        if self.config.getopt('install_only'):
            log.info("Done installing, stopping here per --install-only.")
            self.config.setopt('install_only', True)
            self.loop.exit(0)

        # Update jujus no-proxy setting if applicable
        if self.config.getopt('http_proxy') or \
           self.config.getopt('https_proxy'):
            log.info("Updating juju environments for proxy support")
            lxc_net = self.config.getopt('lxc_network')
            self.config.update_environments_yaml(
                key='no-proxy',
                val='{},localhost,{}'.format(
                    utils.container_ip(self.container_name),
                    netutils.get_ip_set(lxc_net)))

        # start the party
        cloud_status_bin = ['openstack-status']
        self.tasker.start_task("Bootstrapping Juju")
        utils.container_run(self.container_name,
                            "{0} juju bootstrap".format(
                                self.config.juju_home(use_expansion=True)),
                            use_ssh=True)
        utils.container_run(
            self.container_name,
            "{0} juju status".format(
                self.config.juju_home(use_expansion=True)),
            use_ssh=True)
        self.tasker.stop_current_task()

        self.display_controller.status_info_message(
            "Starting cloud deployment")
        utils.container_run_status(
            self.container_name, " ".join(cloud_status_bin), self.config)
