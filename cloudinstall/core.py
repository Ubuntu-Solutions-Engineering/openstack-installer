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
import asyncio
import time
import random
import sys
import requests
from os import getenv, path

from operator import attrgetter

from cloudinstall import utils
from cloudinstall.config import Config
from cloudinstall.juju import JujuState
from cloudinstall.maas import MaasState, MaasMachineStatus
from maasclient.auth import MaasAuth
from maasclient import MaasClient
from cloudinstall.charms import CharmQueue, get_charm

from macumba import JujuClient
from multiprocessing import cpu_count


log = logging.getLogger('cloudinstall.core')
sys.excepthook = utils.global_exchandler


class DisplayController:
    """ Controller for displaying juju and maas state."""

    def __init__(self, ui=None, opts=None):
        self.ui = ui
        self.opts = opts
        self.config = Config()
        self.juju_state = None
        self.juju = None
        self.maas = None
        self.maas_state = None
        self.nodes = None
        self.machine = None
        self.node_install_wait_alarm = None

    def authenticate_juju(self):
        if not len(self.config.juju_env['state-servers']) > 0:
            state_server = 'localhost:17070'
        else:
            state_server = self.config.juju_env['state-servers'][0]
        self.juju = JujuClient(
            url=path.join('wss://', state_server),
            password=self.config.juju_api_password)
        self.juju.login()
        self.juju_state = JujuState(self.juju)
        log.debug('Authenticated against juju api.')

    def authenticate_maas(self):
        auth = MaasAuth()
        auth.get_api_key('root')
        self.maas = MaasClient(auth)
        self.maas_state = MaasState(self.maas)
        log.debug('Authenticated against maas api.')

    def initialize(self):
        """ authenticates against juju/maas and initializes a machine """
        self.authenticate_juju()
        if self.config.is_multi:
            self.authenticate_maas()

    # overlays
    def step_info(self, message):
        self.ui.show_step_info(message)
        self.redraw_screen()

    # - Footer
    def clear_status(self):
        self.ui.clear_status()
        self.redraw_screen()

    def info_message(self, message):
        self.ui.status_info_message(message)
        self.redraw_screen()

    def set_dashboard_url(self, ip):
        self.ui.status_dashboard_url(ip)
        self.redraw_screen()

    def set_jujugui_url(self, ip):
        self.ui.status_jujugui_url(ip)
        self.redraw_screen()

    # - Render
    def render_nodes(self, nodes, juju_state, maas_state):
        self.ui.render_nodes(nodes, juju_state, maas_state)
        self.redraw_screen()

    def render_node_install_wait(self, loop=None, user_data=None):
        self.ui.render_node_install_wait()
        self.redraw_screen()
        self.node_install_wait_alarm = self.loop.set_alarm_in(
            self.config.node_install_wait_interval,
            self.render_node_install_wait)

    def stop_rendering(self, alarm):
        if alarm:
            self.loop.remove_alarm(alarm)
        alarm = None

    def redraw_screen(self):
        if hasattr(self, "loop"):
            if not self.opts.noui:
                try:
                    self.loop.draw_screen()
                except AssertionError as message:
                    logging.critical(message)
            else:
                pass

    def exit(self):
        if not self.opts.noui:
            raise urwid.ExitMainLoop()
        else:
            raise self.loop.stop()

    def main_loop(self):
        if not self.opts.noui:
            if not hasattr(self, 'loop'):
                self.loop = urwid.MainLoop(self.ui,
                                           self.config.STYLES,
                                           handle_mouse=True,
                                           unhandled_input=self.header_hotkeys)
                self.info_message("Welcome ..")
                self.initialize()

            self.render_node_install_wait()
            self.loop.set_alarm_in(3, self.update_alarm)
            self.loop.run()
        else:
            log.debug("Running asyncio event loop for ConsoleUI")
            self.loop = asyncio.get_event_loop()
            self.initialize()
            self.loop.run_forever()

    def start(self):
        """ Starts controller processing """
        self.main_loop()

    def update_alarm(self, *args, **kwargs):
        # Do update here.
        log.debug("Updating node states.")
        self.update_node_states()
        self.loop.set_alarm_in(10, self.update_alarm)

    def update_node_states(self):
        """ Updating node states
        """
        if not self.juju_state:
            return
        deployed_services = sorted(self.juju_state.services,
                                   key=attrgetter('service_name'))
        deployed_service_names = [s.service_name for s in deployed_services]

        charm_classes = sorted([m.__charm_class__ for m in utils.load_charms()
                                if m.__charm_class__.charm_name in
                                deployed_service_names],
                               key=attrgetter('charm_name'))

        self.nodes = list(zip(charm_classes, deployed_services))

        for n in deployed_services:
            for u in n.units:
                if u.is_horizon and u.agent_state == "started":
                    self.set_dashboard_url(u.public_address)
                if u.is_jujugui and u.agent_state == "started":
                    self.set_jujugui_url(u.public_address)
        if len(self.nodes) == 0:
            return
        else:
            self.stop_rendering(self.node_install_wait_alarm)
            self.render_nodes(self.nodes, self.juju_state, self.maas_state)

    def header_hotkeys(self, key):
        if key in ['j', 'down']:
            self.ui.focus_next()
        if key in ['k', 'up']:
            self.ui.focus_previous()
        if key == 'esc':
            self.ui.hide_widget_on_top()
        if key in ['h', 'H', '?']:
            self.ui.show_help_info()
        if key in ['a', 'A', 'f6']:
            charm_modules = utils.load_charms()
            charm_classes = [m.__charm_class__ for m in charm_modules
                             if m.__charm_class__.allow_multi_units and
                             not m.__charm_class__.disabled]
            self.ui.show_add_charm_info(charm_classes, self.add_charm)
        if key in ['q', 'Q']:
            self.exit()
        if key in ['r', 'R', 'f5']:
            self.info_message("View was refreshed.")
            self.render_nodes(self.nodes, self.juju_state, self.maas_state)


class Controller(DisplayController):
    """ Controller for Juju deployments and Maas machine init """

    def __init__(self, **kwds):
        self.charm_modules = utils.load_charms()
        self.deployed_charm_classes = []
        self.finalized_charm_classes = []
        self.single_net_configured = False
        self.lxc_root_tarball_configured = False
        super().__init__(**kwds)

    @utils.async
    def wait_for_maas(self):
        """ install and configure maas """
        random_status = ["Packages are being installed to a MAAS container.",
                         "There's a few packages, it'll take just a minute",
                         "Checkout http://maas.ubuntu.com/ while you wait."]
        is_connected = False
        count = 0
        while not is_connected:
            self.render_node_install_wait()
            self.info_message(
                random_status[random.randrange(len(random_status))])
            count = count + 1
            self.info_message("Waiting for MAAS (tries {0})".format(count))
            uri = path.join('http://', utils.container_ip('maas'), 'MAAS')
            log.debug("Checking MAAS availability ({0})".format(uri))
            try:
                res = requests.get(uri)
                is_connected = res.ok
            except:
                self.info_message("Waiting for MAAS to be installed")
            time.sleep(10)

        # Render nodeview, even though nothing is there yet.
        self.initialize()

    @utils.async
    def init_machine(self):
        """ Handles initial deployment of a machine """
        log.debug("Initializing machine")
        if self.config.is_multi:
            self.info_message("You need one node to act as "
                              "the cloud controller. "
                              "Please PXE boot the node "
                              "you would like to use.")
            nodes = []
            while len(nodes) == 0:
                nodes = self.maas.nodes

            self.maas.tag_fpi(self.maas.nodes)
            self.maas.nodes_accept_all()
            self.maas.tag_name(self.maas.nodes)

        while not self.machine:
            self.machine = self.get_controller_machine()
            time.sleep(15)

        # Step 2
        self.init_machine_setup()

    def get_controller_machine(self):
        allocated = list(self.juju_state.machines_allocated())
        log.debug("Allocated machines: "
                  "{machines}".format(machines=allocated))

        if self.config.is_multi:
            maas_allocated = self.maas_state.machines(MaasMachineStatus.READY)
            if len(allocated) == 0 and len(maas_allocated) == 0:
                err_msg = "No machines allocated to juju. " \
                          "Please pxe boot a machine."
                log.debug(err_msg)
                self.ui.status_error_message(err_msg)
                return None
            elif len(allocated) == 0 and len(maas_allocated) > 0:
                self.info_message("Adding maas machine to juju")
                self.juju.add_machine()
                return None
            else:
                return self.get_started_machine()

        elif self.config.is_single:
            max_cpus = cpu_count()
            if max_cpus >= 2:
                max_cpus = max_cpus // 2

            allocated = list(self.juju_state.machines_allocated())
            if self.config.is_single and len(allocated) == 0:
                self.info_message("Allocating a new machine.")
                self.juju.add_machine(constraints={'mem': 3072,
                                                   'root-disk': 20480,
                                                   'cpu-cores': max_cpus})
            return self.get_started_machine()
        else:
            return None

    def get_started_machine(self):
        started_machines = sorted([m for m in
                                   self.juju_state.machines_allocated()
                                   if m.agent_state == 'started'],
                                  key=lambda m: int(m.machine_id))
        self.info_message("Waiting for an available machine.")

        if len(started_machines) > 0:
            utils.remote_cp(
                started_machines[0].machine_id,
                src="/usr/share/cloud-installer/tools/apt-go-fast",
                dst="/tmp/apt-go-fast")
            utils.remote_run(started_machines[0].machine_id,
                             cmds="sudo sh /tmp/apt-go-fast")
            return started_machines[0]
        return None

    def configure_lxc_network(self):
        # upload our lxc-host-only template and setup bridge
        self.info_message('Copying network specifications to machine.')
        utils.remote_cp(
            self.machine.machine_id,
            src="/usr/share/cloud-installer/templates/lxc-host-only",
            dst="/tmp/lxc-host-only")
        self.info_message('Updating network configuration for machine.')
        utils.remote_run(self.machine.machine_id,
                         cmds="sudo chmod +x /tmp/lxc-host-only")
        utils.remote_run(self.machine.machine_id,
                         cmds="sudo /tmp/lxc-host-only")
        self.single_net_configured = True

    def configure_lxc_root_tarball(self, rootfs):
        """ Use a local copy of the cloud rootfs tarball """
        host = self.machine.dns_name
        cmds = "sudo mkdir -p /var/cache/lxc/cloud-trusty"
        utils.remote_run(self.machine.machine_id, cmds=cmds)
        utils.remote_cp(host, src=rootfs, dst="/var/cache/lxc/cloud-trusty")
        self.lxc_root_tarball_configured = True

    def init_machine_setup(self):
        """ Setup initial machine network and controller """

        self.info_message("Configuring controller machine")
        if self.machine is not None:
            if self.config.is_single and not self.single_net_configured:
                self.configure_lxc_network()

            # Speed up things if we go ahead and download the rootfs image
            # from http://cloud-images.ubuntu.com/releases/trusty/release/
            #
            # Use: export LXC_ROOT_TARBALL=/path/to/rootfs_tarball.tar.gz
            rootfs = getenv('LXC_ROOT_TARBALL', False)
            if rootfs and not self.lxc_root_tarball_configured:
                log.debug("Copying local copy of rootfs")
                self.configure_lxc_root_tarball(rootfs)

            self.info_message('Starting deployment '
                              'on machine {}'.format(
                                  self.machine.machine_id))

        # Step 3
        self.init_deploy_charms()

    def init_deploy_charms(self):
        self.info_message("Verifying service deployments")
        charm_classes = sorted([m.__charm_class__ for m in self.charm_modules
                                if not m.__charm_class__.optional and
                                not m.__charm_class__.disabled],
                               key=attrgetter('deploy_priority'))

        # Add any additional charms enabled from command line
        if self.opts.enable_swift:
            for m in self.charm_modules:
                if m.__charm_class__.name() == "swift-storage" or \
                        m.__charm_class__.name() == "swift-proxy":
                    charm_classes.append(m.__charm_class__)

        undeployed_charm_classes = [c for c in charm_classes
                                    if c not in self.deployed_charm_classes]

        if len(undeployed_charm_classes) > 0:
            for charm_class in undeployed_charm_classes:
                charm = charm_class(juju=self.juju,
                                    juju_state=self.juju_state,
                                    ui=self.ui)
                self.info_message("Checking if {c} "
                                  "is deployed".format(c=charm.display_name))

                service_names = [s.service_name for s in
                                 self.juju_state.services]
                if charm.name() in service_names:
                    self.ui.status_error_message("{c} is already deployed"
                                                 ", skipping".format(c=charm))
                    self.deployed_charm_classes.append(charm_class)
                    continue

                if charm.isolate:
                    self.info_message("Deploying {c} "
                                      "to a new machine".format(
                                          c=charm.display_name))
                    charm.setup()
                else:
                    # Hardcode lxc on same machine as they are
                    # created on-demand.
                    charm.machine_id = 'lxc:{mid}'.format(
                        mid=self.machine.machine_id)
                    self.info_message("Deploying {c} "
                                      "to machine {m}".format(
                                          c=charm.display_name,
                                          m=charm.machine_id))
                    charm.setup()
                self.deployed_charm_classes.append(charm_class)
                self.redraw_screen()

        unfinalized_charm_classes = [c for c in self.deployed_charm_classes
                                     if c not in self.finalized_charm_classes]

        charm_q = CharmQueue()
        if len(unfinalized_charm_classes) > 0:
            self.info_message("Setting charm relations and post processing")
            for charm_class in unfinalized_charm_classes:
                charm = charm_class(juju=self.juju, juju_state=self.juju_state,
                                    ui=self.ui)
                charm_q.add_relation(charm)
                charm_q.add_post_proc(charm)
                self.finalized_charm_classes.append(charm_class)
            if not charm_q.is_running:
                charm_q.watch_relations()
                charm_q.watch_post_proc()
                charm_q.is_running = True

        log.debug("at end of process(), deployed_charm_classes={d}"
                  "finalized_charm_classes={f}".format(
                      d=self.deployed_charm_classes,
                      f=self.finalized_charm_classes))

        if len(self.finalized_charm_classes) == len(charm_classes):
            self.info_message(
                "Services deployed, relationships may still be"
                " pending. Please wait for all services to be checked before"
                " deploying compute nodes.")
            self.render_nodes(self.nodes, self.juju_state, self.maas_state)
            return False
        else:
            log.debug("Polling will continue until all charms are finalized.")
            return True

    def add_charm(self, count=0, charm=None):
        if not charm:
            self.ui.hide_add_charm_info()
            return
        svc = self.juju_state.service(charm)
        if svc.service:
            self.info_message("Adding {n} units of {charm}".format(
                n=count, charm=charm))
            self.juju.add_unit(charm, num_units=int(count))
        else:
            charm_q = CharmQueue()
            charm_sel = get_charm(charm,
                                  self.juju,
                                  self.juju_state,
                                  self.ui)
            log.debug("Add charm: {}".format(charm_sel))
            if not charm_sel.isolate:
                charm_sel.machine_id = 'lxc:{mid}'.format(mid="1")

            self.info_message("Adding {} to environment".format(
                charm_sel))
            charm_q.add_setup(charm_sel)
            charm_q.add_relation(charm_sel)
            charm_q.add_post_proc(charm_sel)

            # Add charm dependencies
            if len(charm_sel.related) > 0:
                for c in charm_sel.related:
                    svc = self.juju_state.service(charm_sel)
                    if not svc.service:
                        self.info_message("Adding dependent "
                                          "charm {c}".format(c=c))
                        charm_dep = get_charm(c,
                                              self.juju,
                                              self.juju_state,
                                              self.ui)
                        if not charm_dep.isolate:
                            charm_dep.machine_id = 'lxc:{mid}'.format(mid="1")
                        charm_q.add_setup(charm_dep)
                        charm_q.add_relation(charm_dep)
                        charm_q.add_post_proc(charm_dep)

            if not charm_q.is_running:
                charm_q.watch_setup()
                charm_q.watch_relations()
                charm_q.watch_post_proc()
                charm_q.is_running = True
        self.ui.hide_add_charm_info()
        return

    def initialize(self):
        """ authenticates against juju/maas and initializes a machine """
        super().initialize()
        self.init_machine()
