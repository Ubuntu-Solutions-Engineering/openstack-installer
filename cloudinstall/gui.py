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

""" Pegasus - gui interface to Ubuntu Cloud Installer """

from collections import deque
from os import write, close
from subprocess import Popen, PIPE, STDOUT
from traceback import format_exc
import re
import threading
import logging

from urwid import (AttrWrap, AttrMap, Text, Columns, Overlay, LineBox,
                   ListBox, Filler, Button, BoxAdapter, Frame, WidgetWrap,
                   SimpleListWalker, Edit, CheckBox,

                   MainLoop, ExitMainLoop)

from cloudinstall.juju.client import JujuClient
from cloudinstall import pegasus
from cloudinstall import utils

log = logging.getLogger('cloudinstall.gui')

TITLE_TEXT = "Ubuntu Cloud Installer"

# - Properties -----------------------------------------------------------------
IS_TTY = re.match('/dev/tty[0-9]', utils.get_command_output('tty')[1])

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
    ('dialog',       'black',      'dark cyan'),
    ('list_title',   'black',      'light gray',),
    ('error',        'white',      'dark red'),
]

RADIO_STATES = list(pegasus.ALLOCATION.values())


def _allocation_for_charms(charms):
    als = [pegasus.ALLOCATION.get(c, '') for c in charms]
    return list(filter(lambda x: x, als))


class TextOverlay(Overlay):
    def __init__(self, text, underlying, width=60, height=5):
        w = LineBox(Filler(Text(text)))
        w = AttrWrap(w, "dialog")
        Overlay.__init__(self,
                               w,
                               underlying,
                               'center',
                               width,
                               'middle',
                               height)


class ControllerOverlay(TextOverlay):
    PXE_BOOT = "You need one node to act as the cloud controller. " \
               "Please PXE boot the node you would like to use."

    NODE_WAIT = "Please wait while the cloud controller is " \
                "installed on your host system."

    NODE_SETUP = "Your node has been correctly detected. " \
                 "Please wait until setup is complete "

    def __init__(self, underlying, command_runner):
        self.underlying = underlying
        self.allocated = None
        self.command_runner = command_runner
        self.done = False
        self.start_text = self.NODE_WAIT \
                          if pegasus.SINGLE_SYSTEM \
                             else self.PXE_BOOT
        TextOverlay.__init__(self, self.start_text, self.underlying)

    def process(self, data):
        """ Process a node list. Returns True if the overlay still needs to be
        shown, false otherwise. """
        if self.done:
            return False

        continue_ = self._process(data)
        if not continue_:
            self.done = True
            log.debug("ControllerOverlay process() is done")
        return continue_

    def _process(self, data):
        import cloudinstall.charms
        helper = utils.ImporterHelper(cloudinstall.charms)
        charms = helper.get_modules()

        allocated = list(data.machines_allocated())
        log.debug("Allocated machines: " \
                  "{machines}".format(machines=allocated))

        if pegasus.MULTI_SYSTEM:
            unallocated = list(data.machines_unallocated())
            log.debug("Unallocated machines: " \
                      "{machines}".format(machines=unallocated))

            if len(allocated) == 0 and len(unallocated) > 0:
                self.command_runner.add_machine()
            elif len(allocated) > 0:
                machine = allocated[0]
                for charm in charms:
                    charm_ = utils.import_module('cloudinstall.charms.{charm}'.format(charm=charm))[0]
                    charm_ = charm_(state=self.state[1])

                    # charm is loaded, decide whether to run it
                    if charm_.name() in machine.charms:
                        continue

                    log.debug("Processing {charm}".format(charm=charm_.name()))

                    machine.machine_id = 'lxc:{_id}'.format(_id=machine.machine_id)

                    # Deploy any remaining charms onto machine except
                    # for nova-compute which would live on a separate
                    # bare-metal machine
                    if 'nova-compute' not in charm_.name():
                        charm_(machine=machine).setup()
                for charm in charms:
                    charm_ = utils.import_module('cloudinstall.charms.{charm}'.format(charm=charm))[0]
                    charm_(state=data).set_relations()
                return False
            else:
                log.debug("No machines, waiting.")
                return True
        elif pegasus.SINGLE_SYSTEM:
            if len(allocated) == 0:
                log.debug("Adding machines")
                self.command_runner.add_machine(constraints={'mem':'6G',
                                                             'root-disk': '20G'})
            else:
                machine = allocated[0]
                log.debug("Making sure {m} is ready".format(m=machine))
                if machine.is_machine_1 \
                   and 'started' in machine.agent_state:
                    # Ok we're up lets upload our lxc-host-only template
                    # and reboot so any containers will be deployed with
                    # the proper subnet
                    utils._run("scp -oStrictHostKeyChecking=no " \
                               "/usr/share/cloud-installer/templates/lxc-host-only " \
                               "ubuntu@{host}:/tmp/lxc-host-only".format(host=machine.dns_name))
                    cmds = []
                    cmds.append("sudo mv /tmp/lxc-host-only /etc/network/interfaces.d/lxcbr0.cfg")
                    cmds.append("sudo rm /etc/network/interfaces.d/eth0.cfg")
                    cmds.append("sudo reboot")
                    utils._run("ssh -oStrictHostKeyChecking=no " \
                               "ubuntu@{host} {cmds}".format(host=machine.dns_name,
                                                             cmds=" && ".join(cmds)))
                else:
                    # machine still hasn't started wait for the loop
                    # to come back around.
                    log.debug("waiting for machine 1 to start")

            for charm in charms:
                charm_ = utils.import_module('cloudinstall.charms.{charm}'.format(charm=charm))[0]
                charm_ = charm_(state=data)

                # charm is loaded, decide whether to run it
                if charm_.name() in [s.service_name for s in data.services]:
                    continue

                log.debug("Processing {charm}".format(charm=charm_.name()))

                # Hardcode lxc on machine 1 as they are
                # created on-demand.
                charm_.setup(_id='lxc:1')
            for charm in charms:
                charm_ = utils.import_module('cloudinstall.charms.{charm}'.format(charm=charm))[0]
                charm_ = charm_(state=data)
                charm_.set_relations()
                charm_.post_proc()

        else:
            log.warning("neither of pegasus.SINGLE_SYSTEM or pegasus.MULTI_SYSTEM are true.")
            return True


def _wrap_focus(widgets, unfocused=None):
    try:
        return [AttrMap(w, unfocused, "focus") for w in widgets]
    except TypeError:
        return AttrMap(widgets, unfocused, "focus")


class AddComputeDialog(Overlay):
    """ Dialog for adding new compute nodes """

    def __init__(self, underlying, state, destroy, command_runner=None):
        self.cr = command_runner
        self.underlying = underlying
        self.destroy = destroy
        self._buttons = [Button("Yes", self.yes),
                         Button("No", self.no)]
        self.wrapped_buttons = _wrap_focus(self._buttons)
        self.buttons = Columns(self.wrapped_buttons)
        self.root = Text("Would you like to add a compute node?")
        self.w = ListBox([self.root, self.buttons])
        self.w = LineBox(self.w)
        self.w = AttrWrap(self.w, "dialog")
        Overlay.__init__(self, self.w, self.underlying,
                               'center', 45, 'middle', 4)

    def yes(self, button):
        log.info("Deploying a new nova compute machine")
        self.cr.add_unit('nova-compute')
        self.destroy()

    def no(self, button):
        self.destroy()

class ChangeStateDialog(Overlay):
    def __init__(self, underlying, machine, on_success, on_cancel):

        self.boxes = []
        start_states = []
        log.debug("ChangeStateDialog.__init__: " \
                  "{machine}".format(machine=machine))
        if machine.charms:
            start_states = _allocation_for_charms(machine.charms)

        self.boxes = []
        first_index = 0
        for i, txt in enumerate(RADIO_STATES):
            if txt in start_states and not first_index:
                first_index = i
            r = CheckBox(txt, state=txt in start_states)
            r.text_label = txt
            self.boxes.append(r)
        wrapped_boxes = _wrap_focus(self.boxes)

        def ok(button):
            selected = filter(lambda r: r.get_state(), self.boxes)
            on_success([s.text_label for s in selected])

        def cancel(button):
            on_cancel()

        bs = [Button("Ok", ok), Button("Cancel", cancel)]
        wrapped_buttons = _wrap_focus(bs)
        self.buttons = Columns(wrapped_buttons)
        self.items = ListBox(wrapped_boxes)
        self.items.set_focus(first_index)
        ba = BoxAdapter(self.items, height=len(wrapped_boxes))
        self.lb = ListBox([ba, Text(""), self.buttons])
        root = LineBox(self.lb, title="Select new charm")
        root = AttrMap(root, "dialog")

        Overlay.__init__(self, root, underlying, 'center', 30, 'middle',
                               len(wrapped_boxes) + 4)

    def keypress(self, size, key):
        if key == 'tab':
            if self.lb.get_focus()[0] == self.buttons:
                self.keypress(size, 'page up')
            else:
                self.keypress(size, 'page down')
        return Overlay.keypress(self, size, key)


class Node(WidgetWrap):
    """ A single ui node representation
    """
    def __init__(self, service=None, state=None, open_dialog=None):
        """
        Initialize Node

        :param service: charm service
        :param type: Service()
        """
        self.service = service
        self.state = state
        self.units = (self.service.units)
        self.open_dialog = open_dialog

        unit_info = []
        for u in self.units:
            info = "{unit_name} " \
                   "({status})".format(unit_name=u.unit_name,
                                         status=u.agent_state)

            info = "{info}\n  address: {address}".format(info=info,
                                                         address=u.public_address)
            if 'error' in u.agent_state:
                info = "{info}\n  info: {state_info}".format(info=info,
                                                             state_info=u.agent_state_info.lstrip())
            info = "{info}\n\n".format(info=info)
            unit_info.append(('weight', 2, Text(info)))

        # machines
        m = [
            (30, Text(self.service.service_name)),
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
        out = self.client.add_machine(constraints)
        return out

    def add_unit(self, service_name, machine_id=None):
        """ Add a unit with optional machine id

        :param str service_name: name of charm
        :param int machine_id: (optional) id of machine to deploy to
        """
        out = self.client.add_unit(service_name, machine_id)
        return out

    def change_allocation(self, new_states, machine):
        """ Changes state allocation of machine

        .. note::

            This only applies to multi-system installs.

        :param list new_states: machine states
        :param machine: Machine()
        """
        log.debug("CommandRunner.change_allocation: " \
                  "new_states: {states}".format(states=new_states))

        if pegasus.MULTI_SYSTEM:
            try:
                log.debug("Validating charm in state: " \
                          "{charms}".format(charms=machine))
                for charm, unit in zip(machine.charms, machine.units):
                    if charm not in new_states:
                        self._run("juju remove-unit " \
                                  "{unit}".format(unit=unit.unit_name))
            except KeyError:
                pass

            if len(new_states) == 0:
                cmd = "juju terminate-machine " \
                      "{id}".format(id=machine.machine_id)
                log.debug("Terminating machine: {cmd}".format(cmd=cmd))
                self._run(cmd)

            state_to_charm = {v: k for k, v in pegasus.ALLOCATION.items()}
            for state in set(new_states) - set(machine.charms):
                charm = state_to_charm[state]
                new_service = charm not in self.services
                if new_service:
                    self.client.deploy(charm,
                                       constraints=dict(tags=machine.tag))
                else:
                    constraints = "juju set-constraints --service " \
                                  "{charm} " \
                                  "tags={{tag}}".format(charm=charm,
                                                        tag=machine.tag)
                    log.debug("Setting constraints: " \
                              "{constraints}".format(constraints=constraints))
                    self._run(constraints.format(tag=machine.tag))
                    cmd = "juju add-unit {charm}".format(charm=charm)
                    log.debug("Adding unit: {cmd}".format(cmd=cmd))
                    self._run(cmd)
                    self._run(constraints.format(tag=''))


# TODO: This and CommandRunner should really be merged
class ConsoleMode(Frame):
    def __init__(self):
        header = [AttrWrap(Text(TITLE_TEXT), "border"),
                  AttrWrap(Text('(Q) Quit'), "border"),
                  AttrWrap(Text('(F8) Node list'), "border")]
        header = Columns(header)
        self.command_runner = CommandRunner()
        Frame.__init__(self, header=header, body=self.command_runner)

    def tick(self):
        pass


class NodeViewMode(Frame):
    def __init__(self, loop, state, command_runner):
        header = [AttrWrap(Text(TITLE_TEXT), "border"),
                  AttrWrap(Text('(Q) Quit'), "border"),
                  AttrWrap(Text('(F5) Refresh'), "border"),
                  AttrWrap(Text('(F8) Console'), "border")]
        if pegasus.SINGLE_SYSTEM:
            header.append(AttrWrap(Text('(F6) Add compute node'), "border"))
        header = Columns(header)
        self.timer = Text("", align="right")
        self.horizon_url = Text("")
        self.jujugui_url = Text("")
        footer = Columns([self.horizon_url,
                                self.jujugui_url,
                                self.timer])
        footer = AttrWrap(footer, "border")
        self.poll_interval = 10
        self.ticks_left = 0
        self.machines, self.state = state
        self.nodes = ListWithHeader(NODE_HEADER)
        self.loop = loop

        self.cr = command_runner
        Frame.__init__(self, header=header, body=self.nodes,
                             footer=footer)
        self.controller_overlay = ControllerOverlay(self, self.cr)
        self._target = self.controller_overlay

    # TODO: get rid of this shim.
    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, val):
        self._target = val
        # Don't switch from command runner back to us "randomly" (i.e. when
        # the setup is complete and the overlay goes away).
        if isinstance(self.loop.widget, ConsoleMode):
            return
        # don't accidentally unlock
        if not isinstance(self.loop.widget, LockScreen):
            self.loop.widget = val

    # FIXME: what is this used for?
    def total_nodes(self):
        return len(self.nodes._contents)

    def destroy(self):
        """ Hides Overlaying dialogs """
        self.loop.widget = self

    def open_dialog(self, machine=None):
        def ok(new_states):
            self.cr.change_allocation(new_states, machine)
            self.destroy()
        if pegasus.MULTI_SYSTEM:
            self.loop.widget = ChangeStateDialog(self,
                                                 machine,
                                                 ok,
                                                 self.destroy)
        else:
            self.loop.widget = AddComputeDialog(self,
                                                self.state,
                                                self.destroy,
                                                self.cr)

    def refresh_states(self):
        """ Refresh states

        Make a call to refresh both juju and maas machine states

        :returns: data from the polling of services and the juju state
        :rtype: tuple (parse_state(), Machine())
        """
        return pegasus.poll_state()

    def do_update(self, state):
        """ Updating node states

        :params list state: JujuState()
        """
        _machines, _state = state
        nodes = [Node(s, _state, self.open_dialog) \
                 for s in _state.services]
        if self.target == self.controller_overlay and \
                not self.controller_overlay.process(_state):
            self.target = self
            for n in _state.services:
                for i in n.units:
                    if i.is_horizon:
                        _url = "Horizon: " \
                               "http://{name}/horizon".format(name=i.public_address)
                        self.horizon_url.set_text(_url)
                    if i.is_jujugui:
                        _url = "Juju-GUI: " \
                               "http://{name}/".format(name=i.public_address)
                        self.jujugui_url.set_text(_url)

        self.nodes.update(nodes)

    def tick(self):
        if self.ticks_left == 0:
            self.ticks_left = self.poll_interval

            def update_and_redraw(state):
                self.do_update(state)
                self.loop.draw_screen()
            self.loop.run_async(self.refresh_states, update_and_redraw)
        self.timer.set_text("Refresh in {secs} (s)".format(secs=self.ticks_left))
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

    IOERROR = ("error", "Problem accessing {pwd}. Please make sure " \
               "it contains exactly one line that is the lock " \
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

    def __init__(self, state=None):
        self.state = state
        self.console = ConsoleMode()
        self.node_view = NodeViewMode(self, self.state,
                                      self.console.command_runner)
        self.lock_ticks = 0  # start in a locked state
        self.locked = False
        MainLoop.__init__(self, self.node_view.target, STYLES,
                                unhandled_input=self._header_hotkeys)

    def _key_pressed(self, keys, raw):
        # We use this as an 'input filter' just to hook when keys are pressed;
        # we don't actually filter any input here.
        self.lock_ticks = LOCK_TIME
        return keys

    def _header_hotkeys(self, key):
        # if we are locked, don't do anything
        if isinstance(self.widget, LockScreen):
            return None
        if key == 'f8':
            if self.widget == self.console:
                self.widget = self.node_view.target
            else:
                self.widget = self.console
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
                old = {'res' : self.widget}

                def unlock():
                    ###########################################################
                    # FIXME: syntax error complains in debian building
                    # probably has something to do with the mixture of
                    # py2 and py3 in our stack.
                    ###########################################################
                    # If the controller overlay finished its work while we were
                    # locked, bypass it.
                    # nonlocal old
                    if isinstance(old['res'], ControllerOverlay) and old['res'].done:
                        old['res'] = self.node_view
                    self.widget = old['res']
                    self.lock_ticks = LOCK_TIME
                    self.locked = False
                self.widget = LockScreen(old['res'], unlock)
            else:
                self.lock_ticks = self.lock_ticks - 1

        self.console.tick()
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

        result = {'res' : None}

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
