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

import glob
from ipaddress import ip_address, ip_network
import json
import logging
import os
import pwd
import re
from subprocess import check_output
from tempfile import TemporaryDirectory

from cloudinstall.config import Config
from cloudinstall.netutils import (get_ip_addr, get_bcast_addr, get_network,
                                   get_default_gateway, get_netmask,
                                   get_network_interfaces,
                                   ip_range_max)
from cloudinstall import utils


log = logging.getLogger('cloudinstall.install')

BRIDGE_MODIFIED_WARNING = """
## WARNING: This file has been modified by cloud-install
##
## cloud-install redefines interfaces in
## /etc/network/interfaces.d/cloud-install.cfg.
## You must edit or remove /etc/network/interfaces.d/cloud-install.cfg if you
## want to re-enable interfaces here.
## See 'cloud-install -u', which will uninstall these changes.
"""


DNS_CONF_TEMPLATE = """
options {{
        directory "/var/cache/bind";
        dnssec-validation auto;

        forwarders {{
        {}
        }};

        include "/etc/bind/maas/named.conf.options.inside.maas";
        auth-nxdomain no;
        listen-on-v6 {{ any; }};
}};
"""


class MultiInstall:

    def __init__(self, opts, display_controller):
        self.opts = opts
        self.display_controller = display_controller
        self.config = Config()
        self.tempdir = TemporaryDirectory(suffix="cloud-install")
        # Sets install type
        utils.spew(os.path.join(self.config.cfg_path,
                                'multi'),
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
                raise MaasInstallError(
                    "Unable to set ownership for {}".format(d))

    def do_install(self):
        # FIXME This is duplicated by write_juju_env
        maas_creds = self.config.maas_creds
        maas_env = utils.load_template('juju-env/maas.yaml')
        maas_env_modified = maas_env.render(
            maas_server=maas_creds['api_host'],
            maas_apikey=maas_creds['api_key'],
            openstack_password=self.config.openstack_password)
        check_output(['mkdir', '-p', self.config.juju_path])
        utils.spew(self.config.juju_environments_path,
                   maas_env_modified)
        utils.ssh_genkey()

        # Set remaining permissions
        self.set_perms()

        # Starts the party
        out = utils.get_command_output("juju --debug bootstrap",
                                       user_sudo=True)
        if out['status'] != 0:
            log.debug("failure to bootstrap: '{}'".format(out))
            raise SystemExit("Problem with juju bootstrap.")

        # workaround to avoid connection failure at beginning of
        # openstack-status
        out = utils.get_command_output("juju status",
                                       user_sudo=True)
        if out['status'] != 0:
            log.debug("failure to get initial juju status: '{}'".format(out))
            raise SystemExit("Problem with juju status poke.")

        self.drop_privileges()

        args = ['openstack-status']
        if self.opts.enable_swift:
            args.append('--enable-swift')
        os.execvp('openstack-status', args)

    def drop_privileges(self):
        if os.geteuid() != 0:
            return

        user_name = os.getenv("SUDO_USER")
        pwnam = pwd.getpwnam(user_name)
        os.initgroups(user_name, pwnam.pw_gid)
        os.setregid(pwnam.pw_gid, pwnam.pw_gid)
        os.setreuid(pwnam.pw_uid, pwnam.pw_uid)


class MultiInstallExistingMaas(MultiInstall):

    def _save_maas_creds(self, maas_server, maas_apikey):
        self.config.save_maas_creds(maas_server, maas_apikey)

        # Saved maas creds, start the show
        self.do_install()

    def run(self):
        self.display_controller.info_message("Please enter your MAAS "
                                             "Server IP and your "
                                             "administrator's API Key")
        self.display_controller.show_maas_input(self._save_maas_creds)


class MaasInstallError(Exception):

    "An error involving installing a new MAAS"


class MultiInstallNewMaas(MultiInstall):

    LOCAL_MAAS_URL = 'http://localhost/MAAS/api/1.0'

    def run(self):
        self.prompt_for_interface()

    def prompt_for_interface(self):
        if_names = sorted(get_network_interfaces().keys())
        self.display_controller.show_selector_info("Choose Interface",
                                                   if_names,
                                                   self.interface_choice_cb)

    def interface_choice_cb(self, choice):
        self.target_iface = choice
        self.iface_ip = get_ip_addr(self.target_iface)
        self.iface_network = get_network(self.target_iface)

        self.continue_with_interface()

    def continue_with_interface(self):
        check_output('mkdir -p /etc/openstack', shell=True)
        check_output(['cp', '/etc/network/interfaces',
                      '/etc/openstack/interfaces.cloud.bak'])
        check_output(['cp', '-r', '/etc/network/interfaces.d',
                      '/etc/openstack/interfaces.cloud.d.bak'])

        utils.spew('/etc/openstack/interface', self.target_iface)

        # Currently assumes that we have installed the maas package already.
        # TODO: will need to install it here at some point

        self.create_superuser()
        self.apikey = self.get_apikey()

        self.login_to_maas(self.apikey)
        cluster_uuid = self.wait_for_registration()
        self.create_maas_bridge(self.target_iface)

        self.prompt_for_bridge()

        self.configure_maas_networking(cluster_uuid,
                                       'br0',
                                       self.gateway,
                                       self.dhcp_range)

        self.configure_dns()

        self.config.save_maas_creds(self.gateway,
                                    self.apikey)

        if "MAAS_HTTP_PROXY" in os.environ:
            pv = os.environ['MAAS_HTTP_PROXY']
            out = utils.get_command_output('maas maas maas set-config '
                                           'name=http_proxy '
                                           'value={}'.format(pv))
            if out['status'] != 0:
                log.debug("Error setting maas proxy config: {}".format(out))
                raise MaasInstallError("Error setting proxy config")

        self.display_controller.info_message("Importing MAAS boot images")
        out = utils.get_command_output('maas maas boot-resources import')
        if out['status'] != 0:
            log.debug("Error starting boot images import: {}".format(out))
            raise MaasInstallError("Error setting proxy config")

        def pred(out):
            return out['output'] != '[]'

        ok = utils.poll_until_true('maas maas boot-images read '
                                   ' {}'.format(cluster_uuid),
                                   pred, 15, timeout=7200)
        if not ok:
            log.debug("poll timed out for getting boot images")
            raise MaasInstallError("Downloading boot images timed out")

        self.display_controller.info_message("Done importing boot images.")

        self.write_juju_env()
        self.create_bootstrap_kvm()

        try:
            utils.chown(os.path.join(utils.install_home(), '.maascli.db'),
                        utils.install_user(),
                        utils.install_user())
        except:
            raise MaasInstallError("Unable to set permissions on {}".format(
                os.path.join(utils.install_home(), '.maascli.db')))

        self.do_install()

    def prompt_for_bridge(self):
        # TODO prompt user to ask about bridging maas nw interface
        self.should_bridge_maasnw = True
        self.display_controller.info_message("Configuring MAAS Network")

        if self.should_bridge_maasnw:
            log.debug("bridging maas network")
            self.configure_nat(get_network('br0'))
            log.debug("configured NAT")
            self.enable_ipv4_forwarding()
            log.debug("enabled forwarding")
            self.gateway = get_ip_addr('br0')
            excludes = [self.iface_ip]
        else:
            self.gateway = get_default_gateway()
            excludes = [self.iface_ip, self.gateway]

        excludes = list(map(ip_address, excludes))
        nw = ip_network(self.iface_network, strict=False)
        self.dhcp_range = ip_range_max(nw, excludes)
        # TODO: allow customization

        self.display_controller.info_message("Detecting Existing DHCP server")
        # TODO UI progress here?
        # TODO Handle existing dhcp with another dialog or user interaction
        # to accept the consequences.
        if self.detect_existing_dhcp(self.target_iface):
            log.error("An existing DHCP server was found on this interface, "
                      "the network may be incorrectly configured.")
            pass

    def create_bootstrap_kvm(self):
        self.display_controller.info_message(
            "Initializing environment for Juju ...")
        out = utils.get_command_output('usermod -a -G libvirtd maas')
        if out['status'] != 0:
            log.debug("error adding maas user to libvirtd: {}".format(out))
            raise MaasInstallError("error in creating bootstrap kvm")

        out = utils.get_command_output('service maas-clusterd restart')
        if out['status'] != 0:
            log.debug("error restarting maas-clusterd: {}".format(out))
            raise MaasInstallError("error in creating bootstrap kvm")

        # TODO investigate if this breaks with someone attempting nested
        # kvm installations. REF http://git.io/8z4xBw
        cmd = ("virt-install --name juju-bootstrap --ram=2048 --vcpus=1 "
               "--hvm --virt-type=kvm --pxe --boot network,hd "
               "--os-variant=ubuntutrusty --graphics vnc --noautoconsole "
               "--os-type=linux --accelerate "
               "--disk=/var/lib/libvirt/images/juju-bootstrap.qcow2,"
               # no space here...
               "bus=virtio,format=qcow2,cache=none,sparse=true,size=20 "
               "--network=bridge=br0,model=virtio")

        out = utils.get_command_output(cmd)
        if out['status'] != 0:
            log.debug("error creating kvm: {}".format(out))
            raise MaasInstallError("error in creating bootstrap kvm")

        out = utils.get_command_output("virsh dumpxml juju-bootstrap "
                                       " | grep 'mac address' | cut -d\\' -f2")
        if out['status'] != 0:
            log.debug("error creating kvm: {}".format(out))
            raise MaasInstallError("error in creating bootstrap kvm")

        kvm_mac = out['output'].strip()

        cmd = ("maas maas nodes new architecture=amd64/generic "
               "mac_addresses={} "
               "hostname=juju-bootstrap nodegroup=$cluster_uuid "
               "power_type=virsh "
               "power_parameters_power_address=qemu:///system "
               "power_parameters_power_id=juju-bootstrap".format(kvm_mac))

        out = utils.get_command_output(cmd)
        if out['status'] != 0:
            log.debug("error creating bootstrap node: {}"
                      "command was:\n{}".format(out, cmd))
            raise MaasInstallError("error in creating bootstrap kvm")

        out = utils.get_command_output('maas maas nodes list '
                                       'mac_address={}'.format(kvm_mac))
        if out['status'] != 0:
            log.debug("error getting system id of kvm: {}".format(out))
            raise MaasInstallError("error in creating bootstrap kvm")

        system_id = json.loads(out['output'])[0]['system_id']

        # out = utils.get_command_output('juju --show-log sync-tools',
        #                                user_sudo=True)
        # if out['status'] != 0:
        #     log.debug("error in sync-tools: {}".format(out))
        #     raise MaasInstallError("error in creating bootstrap kvm")

        def get_node_status(output):
            return json.loads(output)[0]['status']

        # wait until status is 4
        ok = utils.poll_until_true('maas maas nodes list '
                                   'id={}'.format(system_id),
                                   lambda o: get_node_status(o['output']) == 4,
                                   5)
        if not ok:
            log.debug("waiting for status == 4 timed out.")
            raise MaasInstallError("error in bootstrap node creation")

        # currently do_install calls bootstrap, this is saved for reference:
        # self.display_controller.info_message("Bootstrapping Juju")
        # out = utils.get_command_output('juju bootstrap --upload-tools',
        #                                user_sudo=True)
        # if out['status'] != 0:
        #     log.debug("error in juju bootstrap: {}".format(out))
        #     raise MaasInstallError("error in juju bootstrap")

        # wait until status is 6 ('ready')
        # p = lambda o: get_node_status(o['output']) == 6
        # ok = utils.poll_until_true('maas maas nodes list '
        #                            'id={}'.format(system_id),
        #                            p, 5)
        # if not ok:
        #     log.debug("waiting for status == 6 timed out.")
        #     raise MaasInstallError("error in bootstrap node creation")

    def detect_existing_dhcp(self, interface):
        """return True if an existing DHCP server is running on interface."""
        cmd = "nmap --script broadcast-dhcp-discover -e {}".format(interface)
        out = utils.get_command_output(cmd)
        if "DHCPOFFER" in out['output']:
            return True
        return False

    def create_superuser(self):
        pw = self.config.openstack_password
        cmd = ("maas-region-admin createadmin "
               "--username root --password {} "
               "--email root@example.com".format(pw))
        out = utils.get_command_output(cmd)
        if out['status'] != 0:
            log.debug("failed to create maas admin. output"
                      "={}".format(out))

            raise MaasInstallError("Couldn't create admin")

    def get_apikey(self):
        credcmd = ("maas-region-admin apikey "
                   "--username root")
        out = utils.get_command_output(credcmd)
        if out['status'] != 0:
            log.debug("failed to get apikey: {}".format(out))
            raise MaasInstallError("Couldn't get apikey")
        apikey = out['output'].strip()
        return apikey

    def login_to_maas(self, apikey):
        cmd = ("maas login maas {} {}".format(self.LOCAL_MAAS_URL,
                                              apikey))

        out = utils.get_command_output(cmd)
        if out['status'] != 0:
            log.debug("failed to login to maas: {}".format(out))
            raise MaasInstallError("Couldn't log in")

    def wait_for_registration(self):
        cmd = "maas maas node-groups list"

        def get_uuid(odict):
            ostr = odict['output']
            ngs = json.loads(ostr)
            return ngs[0]['uuid']

        def uuid_not_master(odict):
            return get_uuid(odict) != 'master'

        succeeded = utils.poll_until_true(cmd, uuid_not_master, 5)
        if not succeeded:
            msg = "timed out waiting for cluster registration"
            log.debug(msg)
            raise MaasInstallError(msg)

        out = utils.get_command_output(cmd)
        if out['status'] != 0:
            log.debug("failed to get cluster UUID. out={}".format(out))
            raise MaasInstallError("Error in cluster registration")

        return get_uuid(out)

    def create_maas_bridge(self, target_iface):
        """Creates br0 bridge using existing config for 'target_iface'.
        Bridge is defined in
        /etc/network/interfaces.d/openstack.cfg.  Existing config
        for either an existing br0 bridge or the specified target_iface
        will be commented out.
        """
        utils.get_command_output('ifdown {} br0'.format(target_iface))

        cfgfilenames = ['/etc/network/interfaces']
        cfgfilenames += glob.glob('/etc/network/interfaces.d/*.cfg')
        new_bridgefilename = os.path.join(self.tempdir.name, 'bridge.cfg')

        num_bridges = 0
        for cfn in [c for c in cfgfilenames if os.path.exists(c)]:
            created = self.create_bridge_if_exists(target_iface,
                                                   new_bridgefilename,
                                                   cfn)
            num_bridges += (1 if created else 0)

        if num_bridges > 1:
            log.warning("found multiple instances of {}, "
                        "network configuration may "
                        "be wrong".format(target_iface))

        with open('/etc/network/interfaces', 'r+') as e_n_i_file:
            contents = "".join(e_n_i_file.readlines())
            if not re.match('\s*source /etc/network/interfaces.d/\*.cfg',
                            contents):
                e_n_i_file.write("\nsource /etc/network/interfaces.d/*.cfg")

        cloudinst_cfgfilename = "/etc/network/interfaces.d/openstack.cfg"
        with open(new_bridgefilename, 'r') as new_bridge:
            with open(cloudinst_cfgfilename, 'w') as cloudinstall_cfgfile:
                bridge_config = "".join(new_bridge.readlines())
                cloudinstall_cfgfile.write("auto {}\n"
                                           "iface {} inet manual\n\n"
                                           "auto br0\n"
                                           "{}\n"
                                           "bridge_ports "
                                           "{}".format(target_iface,
                                                       target_iface,
                                                       bridge_config,
                                                       target_iface))

        res = utils.get_command_output('ifup {} br0'.format(target_iface))
        if res['status'] != 0:
            log.debug("'ifup {} br0' failed. out={}".format(target_iface, res))
            raise MaasInstallError("Failure in bridge creation")

    def create_bridge_if_exists(self, target, new_bridgefilename,
                                config_filename):
        """look for 'target' in 'config_filename'. if found, comment it out
        and extract its configuration into 'new_bridgefilename', to
        define br0.

        returns True if config_filename has been changed, and false if not.

        """
        new_bridgefile = open(new_bridgefilename, 'w')
        configfile = open(config_filename, 'r')
        new_configfilename = config_filename + "-new-openstack-install"
        new_configfile = open(new_configfilename, 'w')
        copylines = False
        commentlines = False
        changed_config = False
        for line in configfile.readlines():
            c = line.split()
            if len(c) < 2:
                new_configfile.write(line)
                continue

            elif c[0] == 'auto' and c[1] in ['br0', target]:
                new_configfile.write("# {}".format(line))
                changed_config = True
                continue

            elif c[0] == 'iface':
                if c[1] == 'br0':
                    changed_config = True
                    commentlines = True
                    copylines = False
                elif c[1] == target:
                    # print 'iface br0' plus rest of line into new_bridgefile
                    new_bridgefile.write("iface br0 " + " ".join(c[2:]))
                    new_bridgefile.write("\n")
                    changed_config = True
                    copylines, commentlines = True, True
                    continue
                else:
                    copylines, commentlines = False, False

            elif (c[0] in ['mapping', 'auto', 'source'] or
                  c[0].startswith('allow-')):
                copylines, commentlines = False, False

            if commentlines:
                new_configfile.write("# {}".format(line))
                changed_config = True
            else:
                new_configfile.write(line)
            if copylines:
                new_bridgefile.write(line)

        new_bridgefile.close()
        new_configfile.close()
        configfile.close()

        if changed_config:
            with open(new_configfilename, 'r') as new_f:
                with open(config_filename, 'w') as old_f:
                    old_f.write(BRIDGE_MODIFIED_WARNING)
                    old_f.write(''.join(new_f.readlines()))
        return changed_config

    def configure_nat(self, network):
        cmd = ('iptables -t nat -a POSTROUTING '
               '-s {} ! -d {} -j MASQUERADE'.format(network, network))
        utils.get_command_output(cmd)

        utils.spew('/etc/network/iptables.rules',
                   "*nat\n"
                   ":PREROUTING ACCEPT [0:0]\n"
                   ":INPUT ACCEPT [0:0]\n"
                   ":OUTPUT ACCEPT [0:0]\n"
                   ":POSTROUTING ACCEPT [0:0]\n"
                   "-A POSTROUTING -s {} ! -d {} -j MASQUERADE\n"
                   "COMMIT\n".format(network, network))
        utils.get_command_output('chmod 0600 /etc/network/iptables.rules')
        cmd = ("sed -e '/^iface lo inet loopback$/a\ "
               "pre-up iptables-restore < /etc/network/iptables.rules' "
               "-i /etc/network/interfaces")
        res = utils.get_command_output(cmd)
        if res['status'] != 0:
            log.debug("error editing /etc/network/interfaces: {}".format(res))

    def enable_ipv4_forwarding(self):
        cmd = ("sed -e 's/^#net.ipv4.ip_forward=1$/net.ipv4.ip_forward=1/' "
               " -i /etc/sysctl.conf")
        utils.get_command_output(cmd)
        utils.get_command_output('sysctl -p')

    def configure_maas_networking(self, cluster_uuid, interface,
                                  gateway, dhcp_range):
        """ set up or update the node-group-interface.

        dhcp_range is a tuple of ip addresses as strings: (low, high)
        """
        maas_query_cmd = ('maas maas node-group-interfaces'
                          ' list {}'.format(cluster_uuid))
        out = utils.get_command_output(maas_query_cmd)
        interfaces = json.loads(out['output'])
        nmatching = len([i for i in interfaces
                         if i['interface'] == interface])
        interface_exists = nmatching == 1

        paramstr = ('ip={address} interface={interface} '
                    'management=2 subnet_mask={netmask} '
                    'broadcast_ip={bcast} router_ip={gateway} '
                    'ip_range_low={ip_range_low} '
                    'ip_range_high={ip_range_high} ')
        args = dict(uuid=cluster_uuid,
                    interface=interface,
                    address=get_ip_addr(interface),
                    netmask=get_netmask(interface),
                    bcast=get_bcast_addr(interface),
                    gateway=gateway,
                    ip_range_low=dhcp_range[0],
                    ip_range_high=dhcp_range[1])

        if interface_exists:
            cmd = ('maas maas node-group-interface update {uuid} {interface} '
                   + paramstr).format(**args)
        else:
            cmd = ('maas maas node-group-interfaces new {uuid} '
                   + paramstr).format(**args)

        out = utils.get_command_output(cmd)
        if out['status'] != 0:
            log.debug("cmd failed: {}\n - output"
                      "={}".format(cmd, out))
            raise MaasInstallError("unable to create or update network")

    def configure_dns(self):
        with open('/etc/bind/named.conf.options', 'w') as nco_file:
            with open('/etc/resolv.conf', 'r') as resolv_conf_file:
                forwarders = "".join(["\t\t{};\n".format(l.split()[1])
                                      for l in resolv_conf_file.readlines()
                                      if l.startswith('nameserver')])
            nco_file.write(DNS_CONF_TEMPLATE.format(forwarders))
        utils.get_command_output('service bind9 restart')
        utils.get_command_output("sed -e '/^iface lo inet loopback$/a"
                                 "\\n#added by openstack-install\\n"
                                 "dns-nameservers 127.0.0.1' "
                                 " -i /etc/network/interfaces")
        utils.get_command_output('ifdown lo')
        utils.get_command_output('ifup lo')

    def write_juju_env(self):
        # FIXME Duplicated in do_install() we should pick one or the other
        admin_secret = utils.random_password()

        env = utils.load_template('juju-env/maas.yaml')
        env_modified = env.render(
            maas_server=self.config.maas_creds['api_host'],
            maas_apikey=self.apikey,
            openstack_password=admin_secret)
        check_output(['mkdir', '-p', self.config.juju_path])
        utils.spew(self.config.juju_environments_path, env_modified)
