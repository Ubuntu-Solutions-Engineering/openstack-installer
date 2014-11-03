
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
from enum import Enum, unique
import json
import time
import random
import sys
import requests

from contextlib import contextmanager
from os import path, getenv

from operator import attrgetter

from cloudinstall import utils
from cloudinstall.config import Config
from cloudinstall.juju import JujuState
from cloudinstall.maas import MaasState, MaasMachineStatus, MaasMachine
from maasclient.auth import MaasAuth
from maasclient import MaasClient
from cloudinstall.charms import CharmQueue, get_charm
from cloudinstall.log import PrettyLog
from cloudinstall.placement.controller import (PlacementController,
                                               AssignmentType)

from macumba import JujuClient
from macumba import Jobs as JujuJobs


log = logging.getLogger('cloudinstall.core')
sys.excepthook = utils.global_exchandler


@unique
class ControllerState(Enum):

    """Names for current screen state"""
    INSTALL_WAIT = 0
    PLACEMENT = 1
    SERVICES = 2


@contextmanager
def dialog_context(view):
    view.ui.hide_widget_on_top()
    yield
    view.redraw_screen()


@contextmanager
def status_context(view, level='debug', msg=None):
    if msg and level == 'error':
        log.error(msg)
    elif msg and level == 'debug':
        log.debug(msg)
    elif msg and level == 'info':
        log.info(msg)
    elif msg:
        log.warning("Unexpected log level in "
                    "status_context: '{}'".format(level))
    yield
    view.redraw_screen()


@contextmanager
def view_context(view):
    yield
    view.redraw_screen()


class FakeJujuState:
    @property
    def services(self):
        return []

    def machines(self):
        return []

    def invalidate_status_cache(self):
        "does nothing"


class FakeMaasState:

    def machines(self, status=None):
        fakepath = getenv("FAKE_APIS")
        fn = path.join(fakepath, "maas-machines.json")
        with open(fn) as f:
            nodes = json.load(f)
        return [MaasMachine(-1, m) for m in nodes
                if m['hostname'] != 'juju-bootstrap.maas']

    def invalidate_nodes_cache(self):
        "no op"

    def machines_summary(self):
        return "no summary for fake state"


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
        if self.config.maas_creds:
            api_host = self.config.maas_creds['api_host']
            api_url = 'http://{}/MAAS/api/1.0/'.format(api_host)
            api_key = self.config.maas_creds['api_key']
            auth = MaasAuth(api_url=api_url,
                            api_key=api_key)
        else:
            auth = MaasAuth()
            auth.get_api_key('root')
        self.maas = MaasClient(auth)
        self.maas_state = MaasState(self.maas)
        log.debug('Authenticated against maas api.')

    def initialize(self):
        """Authenticates against juju/maas and sets up placement controller."""
        if getenv("FAKE_APIS"):
            self.juju_state = FakeJujuState()
            self.maas_state = FakeMaasState()
        else:
            self.authenticate_juju()
            if self.config.is_multi:
                self.authenticate_maas()

        self.placement_controller = PlacementController(
            self.maas_state, self.opts)

        if path.exists(self.config.placements_filename):
            with open(self.config.placements_filename, 'r') as pf:
                self.placement_controller.load(pf)
            self.info_message("Loaded placements from file.")

        else:
            if self.config.is_multi:
                def_assignments = self.placement_controller.gen_defaults()
            else:
                def_assignments = self.placement_controller.gen_single()

            self.placement_controller.set_all_assignments(def_assignments)

        pfn = self.config.placements_filename
        self.placement_controller.set_autosave_filename(pfn)
        self.placement_controller.do_autosave()

        if self.config.is_single:
            self.begin_deployment()
            return

        if self.opts.edit_placement or \
           not self.placement_controller.can_deploy():
            self.current_state = ControllerState.PLACEMENT
        else:
            self.begin_deployment()

    def begin_deployment(self):
        """To be overridden in subclasses."""

    # overlays

    def step_info(self, message, width, height):
        with dialog_context(self):
            self.ui.show_step_info(message, width, height)

    def show_password_input(self, title, cb):
        with dialog_context(self):
            self.ui.show_password_input(title, cb)

    def show_maas_input(self, title, cb):
        with dialog_context(self):
            self.ui.show_maas_input(title, cb)

    def show_landscape_input(self, title, cb):
        with dialog_context(self):
            self.ui.show_landscape_input(title, cb)

    def show_selector_info(self, title, install_types, cb):
        with dialog_context(self):
            self.ui.show_selector_info(title, install_types, cb)

    def show_exception_message(self, ex):
        def handle_done(*args, **kwargs):
            raise urwid.ExitMainLoop()
        with dialog_context(self):
            logpath = path.join(self.config.cfg_path,
                                "commands.log")
            msg = ("A fatal error has occurred: {}\n"
                   "See {} for further info.".format(ex.args[0],
                                                     logpath))
            self.ui.show_fatal_error_message(msg, handle_done)

    # - Footer
    def clear_status(self):
        self.ui.clear_status()

    def info_message(self, message):
        with status_context(self, 'info', message):
            self.ui.status_info_message(message)

    def error_message(self, message):
        with status_context(self, 'error', message):
            self.ui.status_error_message(message)

    def set_dashboard_url(self, ip):
        with status_context(self):
            self.ui.status_dashboard_url(ip)

    def set_jujugui_url(self, ip):
        with status_context(self):
            self.ui.status_jujugui_url(ip)

    def set_openstack_rel(self, text):
        with status_context(self):
            self.ui.status_openstack_rel(text)

    # - Render
    def render_nodes(self, nodes, juju_state, maas_state):
        with view_context(self):
            self.ui.render_nodes(nodes, juju_state, maas_state)

    def render_node_install_wait(self, message="Waiting..."):
        with view_context(self):
            self.ui.render_node_install_wait(message=message)

    def render_placement_view(self):
        self.ui.render_placement_view(self,
                                      self.placement_controller)
        self.redraw_screen()

    def redraw_screen(self):
        if hasattr(self, "loop"):
            try:
                self.loop.draw_screen()
            except AssertionError as message:
                logging.critical(message)

    def exit(self):
        raise urwid.ExitMainLoop()

    def main_loop(self):
        if not hasattr(self, 'loop'):
            self.loop = urwid.MainLoop(self.ui,
                                       self.config.STYLES,
                                       handle_mouse=True,
                                       unhandled_input=self.header_hotkeys)
            self.info_message("Welcome ..")
            self.initialize()

        self.update()
        self.loop.run()

    def start(self):
        """ Starts controller processing """
        self.main_loop()

    def update(self, *args, **kwargs):
        """Render UI according to current state and reset timer"""
        interval = 1

        if self.current_state == ControllerState.PLACEMENT:
            self.render_placement_view()

        elif self.current_state == ControllerState.INSTALL_WAIT:
            self.render_node_install_wait()
            interval = self.config.node_install_wait_interval

        else:
            self.update_node_states()

        self.loop.set_alarm_in(interval, self.update)

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
            if self.current_state != ControllerState.SERVICES:
                return
            charm_modules = utils.load_charms()
            charm_classes = [m.__charm_class__ for m in charm_modules
                             if m.__charm_class__.allow_multi_units and
                             not m.__charm_class__.disabled]
            self.ui.show_add_charm_info(charm_classes, self.add_charm)
        if key in ['q', 'Q']:
            self.exit()
        if key in ['r', 'R', 'f5']:
            self.info_message("View was refreshed.")
            self.update()


class Controller(DisplayController):

    """ Controller for Juju deployments and Maas machine init """

    def __init__(self, **kwds):
        self.charm_modules = utils.load_charms()
        self.juju_m_idmap = None  # for single, {instance_id: machine id}
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

        elif self.config.is_single:
            self.add_machines_to_juju_single()

        while not self.all_juju_machines_started():
            sd = self.juju_state.machines_summary()
            summary = ", ".join(["{} {}".format(v, k) for k, v
                                 in sd.items()])
            self.info_message("Waiting for machines to "
                              "start: {}".format(summary))
            time.sleep(3)

        self.current_state = ControllerState.SERVICES
        if self.config.is_single:
            controller_machine = self.juju_m_idmap['controller']
            self.configure_lxc_network(controller_machine)

        # FIXME: this is never populated during a multi_install
        # for juju_machine_id in self.juju_m_idmap.values():
        #    self.run_apt_go_fast(juju_machine_id)

        self.deploy_using_placement()
        self.enqueue_deployed_charms()

    def all_maas_machines_ready(self):
        self.maas_state.invalidate_nodes_cache()

        needed = set([m.instance_id for m in
                      self.placement_controller.machines_used()])
        ready = set([m.instance_id for m in
                     self.maas_state.machines(MaasMachineStatus.READY)])
        allocated = set([m.instance_id for m in
                         self.maas_state.machines(MaasMachineStatus.ALLOCATED)
                         ])

        summary = ", ".join(["{} {}".format(v, k) for k, v in
                             self.maas_state.machines_summary().items()])
        self.info_message("Waiting for {} maas machines to be ready."
                          " Machines Summary: {}".format(len(needed),
                                                         summary))
        if not needed.issubset(ready.union(allocated)):
            return False
        return True

    def add_machines_to_juju_multi(self):
        """Adds each of the machines used for the placement to juju, if it
        isn't already there."""

        self.juju_state.invalidate_status_cache()
        juju_ids = [jm.instance_id for jm in self.juju_state.machines()]

        machine_params = []
        for maas_machine in self.placement_controller.machines_used():
            if maas_machine.instance_id in juju_ids:
                # ignore machines that are already added to juju
                continue
            cd = dict(tags=[maas_machine.system_id])
            mp = dict(Series="", ContainerType="", ParentId="",
                      Constraints=cd, Jobs=[JujuJobs.HostUnits])
            machine_params.append(mp)

        if len(machine_params) > 0:
            import pprint
            log.debug("calling add_machines with params:"
                      " {}".format(pprint.pformat(machine_params)))
            rv = self.juju.add_machines(machine_params)
            log.debug("add_machines returned '{}'".format(rv))

    def all_juju_machines_started(self):
        self.juju_state.invalidate_status_cache()
        n_needed = len(self.placement_controller.machines_used())
        n_allocated = len([jm for jm in self.juju_state.machines()
                           if jm.agent_state == 'started'])
        return n_allocated >= n_needed

    def add_machines_to_juju_single(self):
        self.juju_m_idmap = {}
        for jm in self.juju_state.machines():
            response = self.juju.get_annotations(jm.machine_id,
                                                 'machine')
            ann = response['Annotations']
            if 'instance_id' in ann:
                self.juju_m_idmap[ann['instance_id']] = jm.machine_id

        log.debug("existing juju machines: {}".format(self.juju_m_idmap))

        def get_created_machine_id(response):
            d = response['Machines'][0]
            if d['Error']:
                log.debug("Error from add_machine: {}".format(response))
                return None
            else:
                return d['Machine']

        for machine in self.placement_controller.machines_used():
            if machine.instance_id in self.juju_m_idmap:
                machine.machine_id = self.juju_m_idmap[machine.instance_id]
                log.debug("machine instance_id {} already exists as #{}, "
                          "skipping".format(machine.instance_id,
                                            machine.machine_id))
                continue
            log.debug("adding machine with "
                      "constraints={}".format(machine.constraints))
            rv = self.juju.add_machine(constraints=machine.constraints)
            m_id = get_created_machine_id(rv)
            machine.machine_id = m_id
            rv = self.juju.set_annotations(m_id, 'machine',
                                           {'instance_id':
                                            machine.instance_id})
            self.juju_m_idmap[machine.instance_id] = m_id

    def run_apt_go_fast(self, machine_id):
        utils.remote_cp(machine_id,
                        src=path.join(self.config.share_path,
                                      "tools/apt-go-fast"),
                        dst="/tmp/apt-go-fast")
        utils.remote_run(machine_id,
                         cmds="sudo sh /tmp/apt-go-fast")

    def configure_lxc_network(self, machine_id):
        # upload our lxc-host-only template and setup bridge
        self.info_message('Copying network specifications to machine.')
        srcpath = path.join(self.config.tmpl_path, 'lxc-host-only')
        destpath = "/tmp/lxc-host-only"
        utils.remote_cp(machine_id, src=srcpath, dst=destpath)
        self.info_message('Updating network configuration for machine.')
        utils.remote_run(machine_id,
                         cmds="sudo chmod +x /tmp/lxc-host-only")
        utils.remote_run(machine_id,
                         cmds="sudo /tmp/lxc-host-only")

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

        def update_pending_display():
            pending_names = [c.display_name for c in
                             undeployed_charm_classes()]
            self.ui.set_pending_deploys(pending_names)

        while len(undeployed_charm_classes()) > 0:
            update_pending_display()

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
                update_pending_display()

            num_remaining = len(undeployed_charm_classes())
            if num_remaining > 0:
                log.debug("{} charms pending deploy.".format(num_remaining))
                log.debug("deployed_charm_classes={}".format(
                    PrettyLog(self.deployed_charm_classes)))

                time.sleep(5)
            update_pending_display()

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
                    continue
                self.info_message("Deploying {c} "
                                  "to machine {mspec}".format(
                                      c=charm_class.display_name,
                                      mspec=mspec))
                deploy_err = charm.deploy(mspec)
                if deploy_err:
                    errs.append(machine)

        had_err = len(errs) > 0
        if had_err:
            log.warning("deferred deploying to these machines: {}".format(
                errs))
        return had_err

    def get_machine_spec(self, maas_machine, atype):
        """Given a machine and assignment type, return a juju machine spec"""
        jm = next((m for m in self.juju_state.machines()
                   if (m.instance_id == maas_machine.instance_id
                       or
                       m.machine_id == maas_machine.machine_id)), None)
        if jm is None:
            log.error("could not find juju machine matching {}"
                      " (instance id {})".format(maas_machine,
                                                 maas_machine.instance_id))

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
