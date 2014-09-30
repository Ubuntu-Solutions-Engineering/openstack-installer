
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
from enum import Enum, unique
import time
import random
import sys
import requests
from os import path

from operator import attrgetter

from cloudinstall import utils
from cloudinstall.config import Config
from cloudinstall.juju import JujuState
from cloudinstall.maas import MaasState, MaasMachineStatus
from maasclient.auth import MaasAuth
from maasclient import MaasClient
from cloudinstall.charms import CharmQueue, get_charm
from cloudinstall.log import PrettyLog
from cloudinstall.placement.controller import (PlacementController,
                                               AssignmentType)

from macumba import JujuClient
from macumba import Jobs as JujuJobs
from multiprocessing import cpu_count


log = logging.getLogger('cloudinstall.core')
sys.excepthook = utils.global_exchandler


@unique
class ControllerState(Enum):
    """Names for current screen state"""
    INSTALL_WAIT = 0
    PLACEMENT = 1
    SERVICES = 2


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
        self.placement_controller = None
        self.current_state = ControllerState.INSTALL_WAIT

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
        if not self.config.is_multi:
            return

        self.authenticate_maas()

        if not self.opts.placement:
            return

        self.current_state = ControllerState.PLACEMENT
        self.placement_controller = PlacementController(
            self.maas_state, self.opts)
        self.placement_controller.set_all_assignments(
            self.placement_controller.gen_defaults())

    # overlays
    def step_info(self, message):
        self.ui.show_step_info(message)
        self.redraw_screen()

    # - Footer
    def clear_status(self):
        self.ui.clear_status()
        self.redraw_screen()

    def info_message(self, message):
        log.info(message)
        self.ui.status_info_message(message)
        self.redraw_screen()

    def error_message(self, message):
        log.debug(message)
        self.ui.status_error_message(message)
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

    def render_placement_view(self):
        self.ui.render_placement_view(self,
                                      self.placement_controller)
        self.redraw_screen()

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

            self.update_alarm()
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
        interval = 1

        if self.current_state == ControllerState.PLACEMENT:
            self.render_placement_view()

        elif self.current_state == ControllerState.INSTALL_WAIT:
            self.render_node_install_wait()
            interval = self.config.node_install_wait_interval

        else:
            self.update_node_states()

        self.loop.set_alarm_in(interval, self.update_alarm)

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

    def commit_placement(self):
        self.current_state = ControllerState.SERVICES
        self.render_nodes(self.nodes, self.juju_state, self.maas_state)
        self.begin_deployment()

    @utils.async
    def begin_deployment(self):
        log.debug("begin_deployment")
        if self.config.is_multi:

            # now all machines are added
            self.maas.tag_fpi(self.maas.nodes)
            self.maas.nodes_accept_all()
            self.maas.tag_name(self.maas.nodes)

            while not self.all_maas_machines_ready():
                time.sleep(3)

            self.add_machines_to_juju_multi()
            while not self.all_juju_machines_allocated():
                # TODO not sure if this is the right place to use the
                # summary
                summary = self.juju_status.machines_summary()
                self.info_message("Waiting for machines to "
                                  "start: {}".format(summary))
                time.sleep(3)

        elif self.config.is_single:
            self.init_machine_for_single()

        self.deploy_using_placement()
        self.enqueue_deployed_charms()

    def all_maas_machines_ready(self):
        self.maas_state.invalidate_nodes_cache()

        needed = set([m.instance_id for m in
                      self.placement_controller.machines_used()])
        ready = set([m.instance_id for m in
                     self.maas_state.machines(MaasMachineStatus.READY)])

        self.info_message("Waiting for maas machines: {} of {}"
                          " are ready.".format(len(ready),
                                               len(needed)))

        if needed != ready:
            return False
        return True

    def add_machines_to_juju_multi(self):
        """Adds each of the machines used for the placement to juju, if it
        isn't already there."""

        self.juju_state.invalidate_status_cache()
        juju_ids = [jm.instance_id.split('/')[-2]  # extracts id from urlpath
                    for jm in self.juju_state.machines()]

        machine_params = []
        for maas_machine in self.placement_controller.machines_used():
            if maas_machine in juju_ids:
                # ignore machines that are already added to juju
                continue
            cd = dict(tags=maas_machine.system_id)
            mp = dict(Series="", ContainerType="", ParentId="",
                      Constraints=cd, Jobs=[JujuJobs.HostUnits])
            machine_params.append(mp)

        if len(machine_params) > 0:
            self.juju.add_machines(machine_params)

    def all_juju_machines_allocated(self):
        self.juju_state.invalidate_status_cache()
        n_needed = len(self.placement_controller.machines_used())
        n_allocated = len(self.juju_state.machines_allocated())
        return n_needed == n_allocated

    def init_machine_for_single(self):

        allocated = list(self.juju_state.machines_allocated())
        log.debug("Allocated machines: "
                  "{machines}".format(machines=allocated))

        max_cpus = cpu_count()
        if max_cpus >= 2:
            max_cpus = max_cpus // 2

        if len(allocated) == 0:
            self.info_message("Allocating a new machine.")
            self.juju.add_machine(constraints={'mem': 3072,
                                               'root-disk': 20480,
                                               'cpu-cores': max_cpus})

        controller_machine = None
        while not controller_machine:
            self.juju_state.invalidate_status_cache()
            controller_machine = self.get_started_machine_for_single()
            time.sleep(5)

        self.configure_lxc_network(controller_machine)

    def get_started_machine_for_single(self):
        started_machines = sorted([m for m in
                                   self.juju_state.machines_allocated()
                                   if m.agent_state == 'started'],
                                  key=lambda m: int(m.machine_id))

        if len(started_machines) > 0:
            controller_id = started_machines[0].machine_id
            utils.remote_cp(controller_id,
                            src="/usr/share/cloud-installer/tools/apt-go-fast",
                            dst="/tmp/apt-go-fast")
            utils.remote_run(controller_id,
                             cmds="sudo sh /tmp/apt-go-fast")
            self.info_message("Using machine {} as controller host.".format(
                controller_id))
            return started_machines[0]

        machines_summary_items = self.juju_state.machines_summary().items()
        if len(machines_summary_items) > 0:
            status_string = ", ".join(["{} {}".format(v, k) for k, v in
                                       machines_summary_items])
            self.info_message("Waiting for a machine."
                              " Machines summary: {}".format(status_string))
        else:
            self.info_message("Waiting for a machine.")

        return None

    def configure_lxc_network(self, machine):
        # upload our lxc-host-only template and setup bridge
        self.info_message('Copying network specifications to machine.')
        utils.remote_cp(
            machine.machine_id,
            src="/usr/share/cloud-installer/templates/lxc-host-only",
            dst="/tmp/lxc-host-only")
        self.info_message('Updating network configuration for machine.')
        utils.remote_run(machine.machine_id,
                         cmds="sudo chmod +x /tmp/lxc-host-only")
        utils.remote_run(machine.machine_id,
                         cmds="sudo /tmp/lxc-host-only")

    # def init_deploy_charms(self):
    #     """Deploy charms in order, waiting for any deferred charms.
    #     Then enqueue all charms for further processing and return.
    #     """

    #     self.info_message("Verifying service deployments")
    #     charm_classes = sorted([m.__charm_class__ for m in self.charm_modules
    #                             if not m.__charm_class__.optional and
    #                             not m.__charm_class__.disabled],
    #                            key=attrgetter('deploy_priority'))

    #     # Add any additional charms enabled from command line
    #     if self.opts.enable_swift:
    #         for m in self.charm_modules:
    #             if m.__charm_class__.name() == "swift-storage" or \
    #                     m.__charm_class__.name() == "swift-proxy":
    #                 charm_classes.append(m.__charm_class__)

    #     def undeployed_charm_classes():
    #         return [c for c in charm_classes
    #                 if c not in self.deployed_charm_classes]

    #     while len(undeployed_charm_classes()) > 0:
    #         for charm_class in undeployed_charm_classes():
    #             charm = charm_class(juju=self.juju,
    #                                 juju_state=self.juju_state,
    #                                 ui=self.ui)
    #             self.info_message("Checking if {c} "
    #                               "is deployed".format(c=charm.display_name))

    #             service_names = [s.service_name for s in
    #                              self.juju_state.services]
    #             if charm.name() in service_names:
    #                 self.info_message("{c} is already deployed"
    #                                   ", skipping".format(c=charm))
    #                 self.deployed_charm_classes.append(charm_class)
    #                 continue

    #             if charm.isolate:
    #                 self.info_message("Deploying {c} "
    #                                   "to a new machine".format(
    #                                       c=charm.display_name))
    #                 deploy_err = charm.setup()

    #             else:
    #                 # Hardcode lxc on same machine as they are
    #                 # created on-demand.
    #                 charm.machine_id = 'lxc:{mid}'.format(
    #                     mid=self.machine.machine_id)
    #                 self.info_message("Deploying {c} "
    #                                   "to machine {m}".format(
    #                                       c=charm.display_name,
    #                                       m=charm.machine_id))
    #                 deploy_err = charm.setup()

    #             name = charm.display_name
    #             if deploy_err:
    #                 self.info_message("{} iswaiting for another service,"
    #                                   " re- in a few seconds.".format(name))
    #                 break
    #             else:
    #                 log.debug("Issued deploy for {}".format(name))
    #                 self.deployed_charm_classes.append(charm_class)

    #             self.juju_state.invalidate_status_cache()

    #         num_remaining = len(undeployed_charm_classes())
    #         if num_remaining > 0:
    #             log.debug("{} charms pending deploy.".format(num_remaining))
    #             log.debug("deployed_charm_classes={}".format(
    #                 PrettyLog(self.deployed_charm_classes)))

    #             time.sleep(5)

    def deploy_using_placement(self):
        """Deploy charms using machine placement from placement controller,
        waiting for any deferred charms.  Then enqueue all charms for
        further processing and return.
        """

        self.info_message("Verifying service deployments")
        placed_charm_classes = self.placement_controller.placed_charm_classes()
        charm_classes = sorted(placed_charm_classes,
                               key=attrgetter('deploy_priority'))

        def undeployed_charm_classes():
            return [c for c in charm_classes
                    if c not in self.deployed_charm_classes]

        while len(undeployed_charm_classes()) > 0:
            for charm_class in undeployed_charm_classes():
                self.info_message("Checking if {c} is deployed".format(
                    c=charm_class.display_name))

                service_names = [s.service_name for s in
                                 self.juju_state.services]

                if charm_class.charm_name in service_names:
                    self.info_message("{c} is already deployed, "
                                      "skipping".format(
                                          c=charm_class.display_name))
                    self.deployed_charm_classes.append(charm_class)
                    continue

                err = self.try_deploy(charm_class)
                name = charm_class.display_name
                if err:
                    self.info_message("{} is waiting for another service, will"
                                      " re-try in a few seconds.".format(name))
                    break
                else:
                    log.debug("Issued deploy for {}".format(name))
                    self.deployed_charm_classes.append(charm_class)

                self.juju_state.invalidate_status_cache()

            num_remaining = len(undeployed_charm_classes())
            if num_remaining > 0:
                log.debug("{} charms pending deploy.".format(num_remaining))
                log.debug("deployed_charm_classes={}".format(
                    PrettyLog(self.deployed_charm_classes)))

                time.sleep(5)

    def try_deploy(self, charm_class):
        "returns True if deploy is deferred and should be tried again."

        charm = charm_class(juju=self.juju,
                            juju_state=self.juju_state,
                            ui=self.ui)

        placements = self.placement_controller.machines_for_charm(charm_class)
        errs = []
        for atype, ml in placements.items():
            for machine in ml:
                # get machine spec from atype and machine instance id:
                mspec = self.get_machine_spec(machine, atype)
                if mspec is None:
                    errs.append(machine)
                self.info_message("Deploying {c} "
                                  "to machine {mspec}".format(
                                      c=charm_class.display_name,
                                      mspec=mspec))
                deploy_err = charm.deploy(mspec)
                if deploy_err:
                    errs.append(machine)

        had_err = len(errs) > 0
        if had_err:
            log.warning("saw errors deploying to these machines: {}".format(
                errs))
        return had_err

    def get_machine_spec(self, machine, atype):
        """Given a machine and assignment type, return a juju machine spec"""
        jm = next((jm for jm in self.juju_state.machines()
                   if jm.instance_id.split('/')[-2] == machine.instance_id),
                  None)
        if jm is None:
            log.error("could not find juju machine"
                      " matching {}".format(machine))
            return None

        if atype == AssignmentType.BareMetal:
            return jm.machine_id
        elif atype == AssignmentType.LXC:
            return "lxc:{}".format(jm.machine_id)
        elif atype == AssignmentType.KVM:
            return "kvm:{}".format(jm.machine_id)
        else:
            log.error("unexpected atype: {}".format(atype))
            return None

    def enqueue_deployed_charms(self):
        """Send all deployed charms to CharmQueue for relation setting and
        post-proc.
        """

        log.debug("Starting CharmQueue for relation setting and"
                  " post-processing enqueueing {}".format(
                      [c.charm_name for c in self.deployed_charm_classes]))

        charm_q = CharmQueue(ui=self.ui)
        for charm_class in self.deployed_charm_classes:
            charm = charm_class(juju=self.juju, juju_state=self.juju_state,
                                ui=self.ui)
            charm_q.add_relation(charm)
            charm_q.add_post_proc(charm)

        charm_q.watch_relations()
        charm_q.watch_post_proc()
        charm_q.is_running = True

        self.info_message(
            "Services deployed, relationships may still be"
            " pending. Please wait for all services to be checked before"
            " deploying compute nodes.")
        self.render_nodes(self.nodes, self.juju_state, self.maas_state)

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
            charm_q = CharmQueue(ui=self.ui)
            charm_sel = get_charm(charm,
                                  self.juju,
                                  self.juju_state,
                                  self.ui)
            log.debug("Add charm: {}".format(charm_sel))
            if not charm_sel.isolate:
                charm_sel.machine_id = 'lxc:{mid}'.format(mid="1")

            self.info_message("Adding {} to environment".format(
                charm_sel))
            charm_q.add_deploy(charm_sel)
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
                        charm_q.add_deploy(charm_dep)
                        charm_q.add_relation(charm_dep)
                        charm_q.add_post_proc(charm_dep)

            if not charm_q.is_running:
                charm_q.watch_deploy()
                charm_q.watch_relations()
                charm_q.watch_post_proc()
                charm_q.is_running = True
        self.ui.hide_add_charm_info()
        return

    def initialize(self):
        """ authenticates against juju/maas and begins deployment """
        super().initialize()
        if not self.opts.placement or self.config.is_single:
            self.begin_deployment()
