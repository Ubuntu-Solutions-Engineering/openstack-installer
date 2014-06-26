#
# gui.py - Cloud install gui components
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

""" Pegasus - gui interface to  Installer """

from operator import attrgetter
from os import write, close, getenv
from traceback import format_exc
import re
import threading
import logging
from multiprocessing import cpu_count

from urwid import (AttrWrap, AttrMap, Text, Columns, Overlay, LineBox,
                   ListBox, Filler, Button, BoxAdapter, Frame, WidgetWrap,
                   SimpleListWalker, Edit, RadioButton, IntEdit,
                   MainLoop, ExitMainLoop)

from cloudinstall.juju.client import JujuClient
from cloudinstall import pegasus
from cloudinstall import utils
from cloudinstall.charms import CharmQueue, get_charm

log = logging.getLogger('cloudinstall.gui')

TITLE_TEXT = "Ubuntu Openstack Installer"

# - Properties ----------------------------------------------------------------
IS_TTY = re.match('/dev/tty[0-9]', utils.get_command_output('tty')['stdout'])

# Time to lock in seconds
LOCK_TIME = 120

NODE_HEADER = [
    (30, AttrMap(Text("Service"), "list_title")),
    AttrMap(Text("Units"), "list_title"),
]

STYLES = [
    ('body',         'white',      'black',),
    ('border',       'brown',      'dark magenta'),
    ('focus',        'black',      'dark green'),
    ('dialog',       'black',      'light gray'),
    ('list_title',   'black',      'light gray',),
    ('error',        'white',      'dark red'),
]

RADIO_STATES = list(pegasus.ALLOCATION.values())


def _allocation_for_charms(charms):
    als = [pegasus.ALLOCATION.get(c, '') for c in charms]
    return list(filter(lambda x: x, als))


class ControllerOverlay(Overlay):
    PXE_BOOT = "You need one node to act as the cloud controller. " \
               "Please PXE boot the node you would like to use."

    NODE_WAIT = "Please wait while the cloud controller is " \
                "installed on your host system."

    NODE_SETUP = "Your node has been correctly detected. " \
                 "Please wait until setup is complete "

    def __init__(self, underlying, command_runner, opts):
        self.opts = opts
        self.underlying = underlying
        self.command_runner = command_runner
        self.done = False
        self.machine = None
        self.deployed_charm_classes = []
        self.finalized_charm_classes = []
        self.single_net_configured = False
        self.lxc_root_tarball_configured = False
        self.info_text = Text(self.NODE_WAIT
                              if pegasus.SINGLE_SYSTEM
                              else self.PXE_BOOT)
        w = LineBox(Filler(self.info_text))
        w = AttrWrap(w, "dialog")
        Overlay.__init__(self,
                         w,
                         self.underlying,
                         'center',
                         60,
                         'middle',
                         5)

    def process(self, juju_state, maas_state):
        """ Process a node list. Returns True if the overlay still needs to be
        shown, false otherwise. """
        if self.done or len(list(juju_state.services)) >= 9:
            return False

        continue_ = self._process(juju_state, maas_state)
        if not continue_:
            self.done = True
            log.debug("ControllerOverlay process() is done")
        return continue_

    def _process(self, juju_state, maas_state):
        charm_modules = utils.load_charms()
        charm_classes = sorted([m.__charm_class__ for m in charm_modules
                                if not m.__charm_class__.optional and
                                not m.__charm_class__.disabled],
                               key=attrgetter('deploy_priority'))
        # Add any additional charms enabled from command line
        if self.opts.enable_swift:
            for m in charm_modules:
                if m.__charm_class__.name() == "swift-storage" or \
                        m.__charm_class__.name() == "swift-proxy":
                    charm_classes.append(m.__charm_class__)

        if self.machine is None:
            self.machine = self.get_controller_machine(juju_state, maas_state)

            if self.machine is None:
                return True     # keep polling

            if pegasus.SINGLE_SYSTEM and not self.single_net_configured:
                self.configure_lxc_network()

            # Speed up things if we go ahead and download the rootfs image
            # from http://cloud-images.ubuntu.com/releases/trusty/release/
            #
            # Use: export LXC_ROOT_TARBALL=/path/to/rootfs_tarball.tar.gz
            rootfs = getenv('LXC_ROOT_TARBALL', False)
            if rootfs and not self.lxc_root_tarball_configured:
                log.debug("Copying local copy of rootfs")
                self.configure_lxc_root_tarball(rootfs)

            log.debug("starting install on "
                      "machine {mid}".format(mid=self.machine.machine_id))

        undeployed_charm_classes = [c for c in charm_classes
                                    if c not in self.deployed_charm_classes]

        if len(undeployed_charm_classes) > 0:
            self.info_text.set_text("Deploying charms")
            log.debug("Deploying charms")
            for charm_class in undeployed_charm_classes:
                charm = charm_class(juju_state=juju_state)
                log.debug("checking if {c} is deployed:".format(c=charm))

                service_names = [s.service_name for s in juju_state.services]
                if charm.name() in service_names:
                    log.debug("{c} is already deployed, skipping"
                              "".format(c=charm))
                    self.deployed_charm_classes.append(charm_class)
                    continue

                log.debug("Deploying {c}".format(c=charm))

                if charm.isolate:
                    charm.setup()
                else:
                    # Hardcode lxc on same machine as they are
                    # created on-demand.
                    charm.machine_id = 'lxc:{mid}'.format(
                        mid=self.machine.machine_id)
                    charm.setup()
                self.deployed_charm_classes.append(charm_class)

        unfinalized_charm_classes = [c for c in self.deployed_charm_classes
                                     if c not in self.finalized_charm_classes]

        charm_q = CharmQueue()
        if len(unfinalized_charm_classes) > 0:
            self.info_text.set_text("Setting charm relations "
                                    "and post processing")
            for charm_class in unfinalized_charm_classes:
                charm = charm_class(juju_state=juju_state)
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
            log.debug("Charm setup done.")
            return False
        else:
            log.debug("Polling will continue until all charms are finalized.")
            return True

    def get_controller_machine(self, juju_state, maas_state):

        allocated = list(juju_state.machines_allocated())
        log.debug("Allocated machines: "
                  "{machines}".format(machines=allocated))

        if pegasus.MULTI_SYSTEM:
            maas_allocated = list(maas_state.machines_allocated())
            if len(allocated) == 0 and len(maas_allocated) == 0:
                err_msg = "No machines allocated to juju. " \
                          "Please pxe boot a machine."
                log.debug(err_msg)
                self.info_text.set_text(err_msg)
                return None
            elif len(allocated) == 0 and len(maas_allocated) > 0:
                self.info_text.set_text("Adding maas machine to juju")
                self.command_runner.add_machine()
                return None
            else:
                return self.get_started_machine(allocated)

        elif pegasus.SINGLE_SYSTEM:
            return self.get_started_machine(allocated)

        return None

    def get_started_machine(self, allocated):
        started_machines = sorted([m for m in allocated
                                   if m.agent_state == 'started'],
                                  key=lambda m: int(m.machine_id))
        if len(started_machines) == 0:
            self.info_text.set_text("Waiting for a machine "
                                    "to become ready.")
            return None

        return started_machines[0]

    def configure_lxc_network(self):
        # upload our lxc-host-only template and setup bridge
        utils.remote_cp(
            self.machine.machine_id,
            src="/usr/share/cloud-installer/templates/lxc-host-only",
            dst="/tmp/lxc-host-only")
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


def _wrap_focus(widgets, unfocused=None):
    try:
        return [AttrMap(w, unfocused, "focus") for w in widgets]
    except TypeError:
        return AttrMap(widgets, unfocused, "focus")


class AddCharmDialog(Overlay):
    """ Adding charm dialog """

    def __init__(self, underlying, juju_state, destroy, command_runner=None):
        charm_modules = utils.load_charms()
        self.charm_classes = [m.__charm_class__ for m in charm_modules
                              if m.__charm_class__.allow_multi_units and
                              not m.__charm_class__.disabled]

        self.juju_state = juju_state
        self.cr = command_runner
        self.underlying = underlying
        self.destroy = destroy

        self.boxes = []
        self.bgroup = []
        first_index = 0
        for i, charm_class in enumerate(self.charm_classes):
            charm = charm_class(juju_state=juju_state)
            if charm.name() and not first_index:
                first_index = i
            r = RadioButton(self.bgroup, charm.name())
            r.text_label = charm.name()
            self.boxes.append(r)

        self.count_editor = IntEdit("Number of units to add: ", 1)
        self.boxes.append(self.count_editor)
        wrapped_boxes = _wrap_focus(self.boxes)

        bs = [Button("Ok", self.yes), Button("Cancel", self.no)]
        wrapped_buttons = _wrap_focus(bs)
        self.buttons = Columns(wrapped_buttons)
        self.items = ListBox(wrapped_boxes)
        self.items.set_focus(first_index)
        ba = BoxAdapter(self.items, height=len(wrapped_boxes))
        self.lb = ListBox([ba, Text(""), self.buttons])
        self.w = LineBox(self.lb, title="Add unit")
        self.w = AttrMap(self.w, "dialog")
        Overlay.__init__(self, self.w, self.underlying,
                         'center', 45, 'middle', len(wrapped_boxes) + 4)

    def yes(self, button):
        selected = [r for r in self.boxes if
                    r is not self.count_editor
                    and r.get_state()][0]
        _charm_to_deploy = selected.label
        n = self.count_editor.value()
        svc = self.juju_state.service(_charm_to_deploy)
        if svc.service:
            log.info("Adding {n} units of {charm}".format(
                     n=n, charm=_charm_to_deploy))
            self.cr.add_unit(_charm_to_deploy, count=int(n))
        else:
            charm_q = CharmQueue()
            charm = get_charm(_charm_to_deploy,
                              self.juju_state)
            if not charm.isolate:
                charm.machine_id = 'lxc:{mid}'.format(mid="1")

            charm_q.add_setup(charm)
            charm_q.add_relation(charm)
            charm_q.add_post_proc(charm)

            # Add charm dependencies
            if len(charm.related) > 0:
                for c in charm.related:
                    svc = self.juju_state.service(_charm_to_deploy)
                    if not svc.service:
                        log.info("Adding dependent charm {c}".format(c=c))
                        charm_dep = get_charm(c,
                                              self.juju_state)
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
        self.destroy()

    def no(self, button):
        self.destroy()


class Node(WidgetWrap):
    """ A single ui node representation
    """
    def __init__(self, service=None, open_dialog=None, juju_state=None):
        """
        Initialize Node

        :param service: charm service
        :param type: Service()
        """
        self.open_dialog = open_dialog

        unit_info = []
        for u in sorted(service.units, key=attrgetter('unit_name')):
            info = "{unit_name} " \
                   "({status})".format(unit_name=u.unit_name,
                                       status=u.agent_state)

            if u.public_address:
                info += "\naddress: {address}".format(address=u.public_address)

            if 'error' in u.agent_state:
                state_info = u.agent_state_info.lstrip()
                info += "\ninfo: {state_info}".format(state_info=state_info)

            unit_machine = juju_state.machine(u.machine_id)
            if unit_machine.agent_state is None and \
               unit_machine.agent_state_info is not None:
                info += "\nmachine info: " + unit_machine.agent_state_info

            info += "\n\n"
            unit_info.append(('weight', 2, Text(info)))

        # machines
        m = [
            (30, Text(service.service_name)),
            Columns(unit_info)
        ]

        cols = Columns(m)
        self.__super.__init__(cols)

    def selectable(self):
        return True

    def keypress(self, size, key):
        """ Signal binding for Node

        Keys:

        * Enter - Opens node state change dialog
        * F6 - Opens charm deployments dialog
        * i - Node info on highlighted service
        """
        if key == 'f6':
            self.open_dialog()
        if key in ['i', 'I']:
            log.debug(self._w)
        return key


class ListWithHeader(Frame):
    def __init__(self, header_text):
        self._contents = SimpleListWalker([])
        body = ListBox(self._contents)
        Frame.__init__(self, header=Columns(header_text), body=body)

    def selectable(self):
        return len(self._contents) > 0

    def update(self, nodes):
        self._contents[:] = _wrap_focus(nodes)


class CommandRunner(ListBox):
    def __init__(self):
        self._contents = SimpleListWalker([])
        ListBox.__init__(self, self._contents)
        self.client = JujuClient()

    def add_machine(self, constraints=None):
        """ Add a machine with optional constraints

        :param dict constraints: (optional) machine specs
        """
        log.debug("adding machine with constraints={}".format(constraints))
        out = self.client.add_machine(constraints)
        return out

    def add_unit(self, service_name, machine_id=None, count=1):
        """ Add a unit with optional machine id

        :param str service_name: name of charm
        :param int machine_id: (optional) id of machine to deploy to
        :param int count: (optional) number of units to add
        """
        out = self.client.add_unit(service_name, machine_id, count)
        return out


class NodeViewMode(Frame):
    def __init__(self, loop, opts):
        header = [AttrWrap(Text(TITLE_TEXT), "border"),
                  AttrWrap(Text('(F6) Add units'), "border"),
                  AttrWrap(Text('(F5) Refresh'), "border"),
                  AttrWrap(Text('(Q) Quit'), "border")]
        header = Columns(header)
        self.status_info = Text("", align="left")
        self.horizon_url = Text("", align="right")
        self.jujugui_url = Text("", align="right")
        footer = Columns([('weight', 0.2, self.status_info),
                          ('weight', 0.2, self.horizon_url),
                          ('weight', 0.2, self.jujugui_url)])
        footer = AttrWrap(footer, "border")
        self.poll_interval = 10
        self.ticks_left = 0
        self.juju_state = None
        self.maas_state = None
        self.nodes = ListWithHeader(NODE_HEADER)
        self.loop = loop
        self.opts = opts

        self.cr = CommandRunner()
        Frame.__init__(self, header=header, body=self.nodes,
                       footer=footer)
        self.controller_overlay = ControllerOverlay(self, self.cr, self.opts)
        self._target = self.controller_overlay

    # TODO: get rid of this shim.
    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, val):
        self._target = val
        # don't accidentally unlock
        if not isinstance(self.loop.widget, LockScreen):
            self.loop.widget = val

    # FIXME: what is this used for?
    def total_nodes(self):
        return len(self.nodes._contents)

    def destroy(self):
        """ Hides Overlaying dialogs """
        self.loop.widget = self

    def open_dialog(self):
            self.loop.widget = AddCharmDialog(self,
                                              self.juju_state,
                                              self.destroy,
                                              self.cr)

    def refresh_states(self):
        """ Refresh states

        Make a call to refresh both juju and maas machine states

        :returns: data from the polling of services and the juju state
        :rtype: tuple (JujuState(), MaasState())
        """
        log.debug("Syncing juju state.")
        return pegasus.poll_state()

    def do_update(self, juju_state, maas_state):
        """ Updating node states

        :param juju_state: juju polled state
        :type juju_state JujuState()
        :param maas_state: maas polled state
        :type maas_state MaasState()
        """
        deployed_services = sorted(juju_state.services,
                                   key=attrgetter('service_name'))
        deployed_service_names = [s.service_name for s in deployed_services]

        charm_classes = sorted([m.__charm_class__ for m in utils.load_charms()
                                if m.__charm_class__.charm_name in
                                deployed_service_names],
                               key=attrgetter('charm_name'))

        a = sorted([(c.display_priority, c.charm_name,
                     Node(s, self.open_dialog, juju_state))
                    for (c, s) in zip(charm_classes, deployed_services)])
        nodes = [node for (_, _, node) in a]

        if self.target == self.controller_overlay:
            continue_polling = self.controller_overlay.process(juju_state,
                                                               maas_state)
            if continue_polling is False:
                self.target = self
        self.nodes.update(nodes)

    def update_and_redraw(self, state):
        self.status_info.set_text("[INFO] Polling node availability")
        self.juju_state, self.maas_state = state
        self.do_update(self.juju_state, self.maas_state)
        for n in self.juju_state.services:
            for i in n.units:
                if i.is_horizon:
                    url = "Horizon: "
                    if i.public_address:
                        url += "http://{}/horizon".format(i.public_address)
                        self.status_info.set_text("[INFO] Nodes "
                                                  "are accessible")
                    else:
                        url += "Pending"
                        self.status_info.set_text("[INFO] Nodes "
                                                  "are still deploying")
                    self.horizon_url.set_text(url)
                if i.is_jujugui:
                    if i.public_address:
                        url = "Juju-GUI: http://{}/".format(i.public_address)
                    else:
                        url = "Juju-GUI: Pending"
                    self.jujugui_url.set_text(url)
        self.loop.draw_screen()

    def tick(self):
        if self.ticks_left == 0:
            self.ticks_left = self.poll_interval
            self.loop.run_async(self.refresh_states, self.update_and_redraw)
        self.ticks_left = self.ticks_left - 1

    def keypress(self, size, key):
        """ Signal binding for NodeViewMode

        Keys:

        * F5 - Refreshes the node list
        """
        if key == 'f5':
            self.ticks_left = 0
        return Frame.keypress(self, size, key)


class LockScreen(Overlay):
    LOCKED = "The screen is locked. Please enter a password (this is the " \
             "password you entered for OpenStack during installation). "

    INVALID = ("error", "Invalid password.")

    IOERROR = ("error", "Problem accessing {pwd}. Please make sure "
               "it contains exactly one line that is the lock "
               "password.".format(pwd=pegasus.PASSWORD_FILE))

    def __init__(self, underlying, unlock):
        self.unlock = unlock
        self.password = Edit("Password: ", mask='*')
        self.invalid = Text("")
        w = ListBox([Text(self.LOCKED), self.invalid,
                     self.password])
        w = LineBox(w)
        w = AttrWrap(w, "dialog")
        Overlay.__init__(self, w, underlying, 'center', 60, 'middle', 8)

    def keypress(self, size, key):
        if key == 'enter':
            if pegasus.OPENSTACK_PASSWORD is None:
                self.invalid.set_text(self.IOERROR)
            elif pegasus.OPENSTACK_PASSWORD == self.password.get_edit_text():
                self.unlock()
            else:
                self.invalid.set_text(self.INVALID)
                self.password.set_edit_text("")
        else:
            return Overlay.keypress(self, size, key)


class PegasusGUI(MainLoop):
    """ Pegasus Entry class """

    def __init__(self, opts):
        self.opts = opts
        self.cr = CommandRunner()
        self.node_view = NodeViewMode(self, self.opts)
        self.lock_ticks = 0  # start in a locked state
        self.locked = False
        self.juju_state, _ = pegasus.poll_state()
        self.init_machine()
        MainLoop.__init__(self, self.node_view.target, STYLES,
                          unhandled_input=self._header_hotkeys)

    @utils.async
    def init_machine(self):
        """ Handles intial deployment of a machine """
        max_cpus = cpu_count()
        if max_cpus >= 2:
            max_cpus = max_cpus // 2
        if pegasus.MULTI_SYSTEM:
            return
        else:
            allocated = list(self.juju_state.machines_allocated())
            if len(allocated) == 0:
                self.cr.add_machine(constraints={'mem': '3G',
                                                 'root-disk': '20G',
                                                 'cpu-cores': max_cpus})

    def _key_pressed(self, keys, raw):
        # We use this as an 'input filter' just to hook when keys are pressed;
        # we don't actually filter any input here.
        self.lock_ticks = LOCK_TIME
        return keys

    def _header_hotkeys(self, key):
        # if we are locked, don't do anything
        if isinstance(self.widget, LockScreen):
            return None
        if key in ['q', 'Q']:
            raise ExitMainLoop()

    def tick(self, unused_loop=None, unused_data=None):
        #######################################################################
        # FIXME: Build problems with nonlocal keyword
        # see comment under unlock()
        #######################################################################
        # Only lock when we are in TTY mode.
        if not self.locked and IS_TTY:
            if self.lock_ticks == 0:
                self.locked = True
                old = {'res': self.widget}

                def unlock():
                    ###########################################################
                    # FIXME: syntax error complains in debian building
                    # probably has something to do with the mixture of
                    # py2 and py3 in our stack.
                    ###########################################################
                    # If the controller overlay finished its work while we were
                    # locked, bypass it.
                    # nonlocal old
                    if isinstance(old['res'], ControllerOverlay) and \
                       old['res'].done:
                        old['res'] = self.node_view
                    self.widget = old['res']
                    self.lock_ticks = LOCK_TIME
                    self.locked = False
                self.widget = LockScreen(old['res'], unlock)
            else:
                self.lock_ticks = self.lock_ticks - 1

        self.node_view.tick()
        self.set_alarm_in(1.0, self.tick)

    def run(self):
        self.tick()
        with utils.console_blank():
            MainLoop.run(self)

    def run_async(self, f, callback):
        """ This is a little bit goofy. The urwid API is based on select(), and
        can't actually run python functions asynchronously. So, if we want to
        run a long-running function which should update the UI, we have to get
        a fd to have urwid watch for us, and then we send data to it when it's
        done.

        FIXME: Once https://github.com/wardi/urwid/pull/57 is implemented.
        """

        result = {'res': None}

        # Here again things are a little weird: we own write_fd, but the urwid
        # API makes things a bit awkward since we end up needing mutually
        # recursive values, so we abuse python's scoping rules.
        def done(unused):
            try:
                callback(result['res'])
            except Exception:
                log.warning(format_exc())
            finally:
                self.remove_watch_pipe(write_fd)
                close(write_fd)

        write_fd = self.watch_pipe(done)

        def run_f():
            ###################################################################
            # FIXME: Because we are putting a dependency on python2
            # for whatever reason using nonlocal is turning into a
            # syntax error. I can only assume it has to do with the
            # packaging somehow.
            # nonlocal result
            ###################################################################
            try:
                result['res'] = f()
            except Exception:
                log.debug(format_exc())
            write(write_fd, bytes('done', 'ascii'))

        threading.Thread(target=run_f).start()
