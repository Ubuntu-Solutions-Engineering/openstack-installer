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

from collections import deque
from errno import ENOENT
from os import write, close
from os.path import expanduser
import re
from subprocess import check_call, Popen, PIPE, STDOUT
from time import strftime
from traceback import format_exc
import threading
import urwid

from cloudinstall import pegasus
from cloudinstall import utils

LOG_FILE = expanduser('~/.cloud-install/commands.log')

# Time to lock in seconds
LOCK_TIME = 120

NODE_FORMAT = "|".join(["{fqdn:<20}", "{cpu_count:>6}", "{memory:>10}",
                        "{storage:>12}", "{agent_state:<12}", "{tags}"])
NODE_HEADER = "|".join(["{fqdn:<20}", "{cpu_count:<6}", "{memory:<10}",
                        "{storage:<12}", "{agent_state:<12}",
                        "{tags}"]).format(fqdn="Hostname",
                                          cpu_count="# CPUs",
                                          memory="RAM (MB)",
                                          storage="Storage (GB)",
                                          agent_state="State",
                                          tags="Charms")

STYLES = [
    ('body',         'white',      'black',),
    ('border',       'brown',      'dark magenta'),
    ('focus',        'black',      'dark green'),
    ('dialog',       'black',      'dark cyan'),
    ('list_title',   'black',      'light gray',),
    ('error',        'white',      'dark red'),
]

IS_TTY = re.match('/dev/tty[0-9]', utils._run('tty').decode('ascii'))

TITLE_TEXT = "Pegasus - your cloud's scout"
if not IS_TTY:
    TITLE_TEXT = "%s (q to quit)" % TITLE_TEXT


def _allocation_for_charms(charms):
    als = [pegasus.ALLOCATION.get(c, '') for c in charms]
    return list(filter(lambda x: x, als))


def time():
    return strftime('%Y-%m-%d %H:%M')


class TextOverlay(urwid.Overlay):
    def __init__(self, text, underlying):
        w = urwid.LineBox(urwid.Filler(urwid.Text(text)))
        w = urwid.AttrWrap(w, "dialog")
        urwid.Overlay.__init__(self, w, underlying, 'center', 60, 'middle', 5)


# TODO: Use TextOverlay
class ControllerOverlay(urwid.Overlay):
    PXE_BOOT = "You need one node to act as the cloud controller. " \
               "Please PXE boot the node you would like to use."

    LXC_WAIT = "Please wait while the cloud controller is installed on your " \
               "host system."

    NODE_SETUP = "Your node has been correctly detected. " \
                 "Please wait until setup is complete "

    def __init__(self, underlying, command_runner):
        self.allocated = None
        self.command_runner = command_runner
        self.done = False
        start_text = self.LXC_WAIT if pegasus.SINGLE_SYSTEM else self.PXE_BOOT
        self.text = urwid.Text(start_text)
        w = urwid.Filler(self.text)
        w = urwid.LineBox(w)
        w = urwid.AttrWrap(w, "dialog")
        urwid.Overlay.__init__(self, w, underlying, 'center', 60, 'middle', 5)

    def process(self, data):
        """ Process a node list. Returns True if the overlay still needs to be
        shown, false otherwise. """
        if self.done:
            return False

        # Wait until the command runner is done to do any more processing
        # steps.
        if len(self.command_runner.to_run) > 0:
            return True
        continue_ = self._process(data)
        if not continue_:
            self.done = True
        return continue_

    def _controller_charms_to_allocate(self, data):
        charms = {c for n in data if 'charms' in n for c in n['charms']}
        return set(pegasus.CONTROLLER_CHARMS) - charms

    def _process(self, data):
        def is_allocated(d):
            allocated_states = ['started', 'pending', 'down']
            return 'charms' in d or d['agent_state'] in allocated_states
        allocated, unallocated = utils.partition(is_allocated, data)
        controllers = [n for n in allocated
                       if pegasus.NOVA_CLOUD_CONTROLLER in n.get('charms', [])]

        # First, we do add-machine, so that we can then deploy everything
        # into a container in subsequent steps.
        if (len(allocated) == 0 and len(unallocated) > 0 and
                not pegasus.SINGLE_SYSTEM):
            self.command_runner.add_machine()
        elif len(allocated) > 0:
            id = allocated[0]['machine_no']

            # For single system installs, we use containers on the bare
            # metal (assumed to be machine 1, given to us by the
            # installer). Everywhere else, we just use the first available
            # machine, which is the id of the first machine in the
            # unallocated list.
            if pegasus.SINGLE_SYSTEM:
                assert id == "1"

            pending = self._controller_charms_to_allocate(data)
            if len(pending) == 0:
                return False

            for charm in pending:
                self.command_runner.deploy(charm, id='lxc:%s' % id)

            if pegasus.SINGLE_SYSTEM:
                # Add one compute node in single system mode, all we have to do
                # is start the KVM, the maas poll loop will take it from there.
                pegasus.StartKVM().run()

            self.text.set_text(self.NODE_SETUP)
        return True


def _wrap_focus(widgets, unfocused=None):
    try:
        return [urwid.AttrMap(w, unfocused, "focus") for w in widgets]
    except TypeError:
        return urwid.AttrMap(widgets, unfocused, "focus")


RADIO_STATES = list(pegasus.ALLOCATION.values())


class ChangeStateDialog(urwid.Overlay):
    def __init__(self, underlying, metadata, on_success, on_cancel):
        self.metadata = metadata

        self.boxes = []
        start_states = []
        if 'charms' in metadata:
            start_states = _allocation_for_charms(metadata['charms'])

        self.boxes = []
        first_index = 0
        for i, txt in enumerate(RADIO_STATES):
            if txt in start_states and not first_index:
                first_index = i
            r = urwid.CheckBox(txt, state=txt in start_states)
            r.text_label = txt
            self.boxes.append(r)
        wrapped_boxes = _wrap_focus(self.boxes)

        def ok(button):
            states = map(lambda b: b.get_state(), self.boxes)
            selected = filter(lambda r: r.get_state(), self.boxes)
            on_success([s.text_label for s in selected])

        def cancel(button):
            on_cancel()

        bs = [urwid.Button("Ok", ok), urwid.Button("Cancel", cancel)]
        wrapped_buttons = _wrap_focus(bs)
        self.buttons = urwid.Columns(wrapped_buttons)
        self.items = urwid.ListBox(wrapped_boxes)
        self.items.set_focus(first_index)
        ba = urwid.BoxAdapter(self.items, height=len(wrapped_boxes))
        self.lb = urwid.ListBox([ba, urwid.Text(""), self.buttons])
        root = urwid.LineBox(self.lb, title="Select new charm")
        root = urwid.AttrMap(root, "dialog")

        urwid.Overlay.__init__(self, root, underlying, 'center', 30, 'middle',
                               len(wrapped_boxes) + 4)

    def keypress(self, size, key):
        if key == 'tab':
            if self.lb.get_focus()[0] == self.buttons:
                self.keypress(size, 'page up')
            else:
                self.keypress(size, 'page down')
        return urwid.Overlay.keypress(self, size, key)


class Node(urwid.Text):
    """ Metadata is a dict with the following:
        charm: the charm name of this node, if it has one,
        fqdn: fully qualified domain name,
        cpu_count, memory (in MB), storage (in GB),
        id: the MAAS resource_uri/juju instance-id
    """
    def __init__(self, metadata, open_dialog):
        urwid.Text.__init__(self, "")
        self.allocated = 'charms' in metadata
        if self.allocated:
            self._selectable = metadata['charms'] not in pegasus.CONTROLLER_CHARMS
        else:
            self._selectable = True
        self.metadata = metadata
        self.open_dialog = open_dialog

    @property
    def is_horizon(self):
        return self.allocated and \
            pegasus.OPENSTACK_DASHBOARD in self.metadata['charms']

    @property
    def is_compute(self):
        return self.allocated and \
            pegasus.NOVA_COMPUTE in self.metadata['charms']

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, val):
        self._metadata = val
        md = self._metadata.copy()
        tags = ''
        if 'charms' in self._metadata:
            tags = ', '.join(self._metadata['charms'])
        self.set_text(NODE_FORMAT.format(tags=tags, **md))
        return self._metadata

    @property
    def name(self):
        return self.metadata['fqdn']

    def keypress(self, size, key):
        # can't change node state on single system
        if key == 'enter' and not pegasus.SINGLE_SYSTEM:
            self.open_dialog(self.metadata)
        return key


class ListWithHeader(urwid.Frame):
    def __init__(self, header_text):
        header = urwid.AttrMap(urwid.Text(header_text), "list_title")
        self._contents = urwid.SimpleListWalker([])
        body = urwid.ListBox(self._contents)
        urwid.Frame.__init__(self, header=header, body=body)

    def selectable(self):
        return len(self._contents) > 0

    def update(self, nodes):
        self._contents[:] = _wrap_focus(nodes)


class CommandRunner(urwid.ListBox):
    def __init__(self):
        self._contents = urwid.SimpleListWalker([])
        urwid.ListBox.__init__(self, self._contents)
        self.to_run = deque()
        self.running = None
        self.services = set()
        self.to_add = []

    def keypress(self, size, key):
        if key.lower() == "ctrl u":
            key = 'page up'
        if key.lower() == "ctrl d":
            key = 'page down'
        return urwid.ListBox.keypress(self, size, key)

    def _add(self, command, output):

        def add_to_f8(command, output):
            txt = "%s> %s\n%s" % (time(), command, output)
            self._contents.append(urwid.Text(txt))
            self._contents[:] = self._contents[:200]
            return txt

        txt = add_to_f8(command, output)
        try:
            with open(LOG_FILE, "a") as f:
                f.write(txt + "\n")
        except IOError as e:
            add_to_f8('log writer:',
                      'Problem accessing %s:\n%s' % (LOG_FILE, e))

    def _run(self, command):
        self.to_run.append(command)
        self._next()

    def _next(self):
        if not self.running and len(self.to_run) > 0:
            cmd = self.to_run.popleft()
            try:
                self.running = Popen(cmd.split(), stdout=PIPE, stderr=STDOUT)
                self.running.command = cmd
            except (IOError, OSError) as e:
                self.running = None
                self._add(cmd, str(e))

    def add_machine(self):
        self._run("juju add-machine")

    def deploy(self, charm, id=None, tag=None):
        config = pegasus.juju_config_arg(charm)
        to = "" if id is None else "--to " + str(id)
        constraints = "" if tag is None else "--constraints tags=" + tag
        cmd = "juju deploy {config} {to} {constraints} {charm}".format(
            config=config, to=to, constraints=constraints, charm=charm)
        self._run(cmd)
        self.services.add(charm)
        self.to_add.extend(pegasus.get_charm_relations(charm))
        remaining = []
        for (relation, cmd) in self.to_add:
            if relation in self.services:
                self._run(cmd)
            else:
                remaining.append((relation, cmd))
        self.to_add = remaining

    def change_allocation(self, new_states, metadata):
        try:
            for charm, unit in zip(metadata['charms'], metadata['units']):
                if charm not in new_states:
                    self._run("juju remove-unit {unit}".format(unit=unit))
        except KeyError:
            pass

        if len(new_states) == 0:
            cmd = "juju terminate-machine {id}"
            self._run(cmd.format(id=metadata['machine_no']))

        state_to_charm = {v: k for k, v in pegasus.ALLOCATION.items()}
        for state in set(new_states) - set(metadata.get('charms', [])):
            charm = state_to_charm[state]
            new_service = charm not in self.services
            if new_service:
                if pegasus.SINGLE_SYSTEM:
                    self.deploy(charm, id='lxc:1')
                else:
                    self.deploy(charm, tag=metadata['tag'])
            else:
                # TODO: we should make this a bit nicer, and do the
                # SINGLE_SYSTEM test a little higher up.
                if pegasus.SINGLE_SYSTEM:
                    cmd = "juju add-unit --to lxc:1 " \
                          "{charm}".format(to=to, charm=charm)
                    self._run(cmd)
                else:
                    constraints = "juju set-constraints --service " \
                                  "{charm} tags={{tag}}".format(charm=charm)
                    self._run(constraints.format(tag=metadata['tag']))
                    self._run("juju add-unit {charm}".format(charm=charm))
                    self._run(constraints.format(tag=''))

    def update(self, juju_state):
        self.services = set(juju_state.services.keys())

    def poll(self):
        if self.running and self.running.poll() is not None:
            out = self.running.stdout.read().decode('ascii')
            self._add(self.running.command, out)
            self.running = None
            self._next()


def _make_header(rest):
    header = urwid.Text("%s %s" % (TITLE_TEXT, rest))
    return urwid.AttrWrap(header, "border")


# TODO: This and CommandRunner should really be merged
class ConsoleMode(urwid.Frame):
    def __init__(self):
        header = _make_header("(f8 switches to node view mode)")
        self.command_runner = CommandRunner()
        urwid.Frame.__init__(self, header=header, body=self.command_runner)

    def tick(self):
        self.command_runner.poll()


class NodeViewMode(urwid.Frame):
    def __init__(self, loop, get_data, command_runner):
        f6 = ', f6 to add another node' if pegasus.SINGLE_SYSTEM else ''
        header = _make_header("(f8 switches to console mode%s)" % f6)

        self.timer = urwid.Text("", align="right")
        self.url = urwid.Text("")
        footer = urwid.Columns([self.url, self.timer])
        footer = urwid.AttrWrap(footer, "border")
        self.poll_interval = 10
        self.ticks_left = 0
        self.get_data = get_data
        self.nodes = ListWithHeader(NODE_HEADER)
        self.loop = loop

        self.cr = command_runner
        urwid.Frame.__init__(self, header=header, body=self.nodes,
                             footer=footer)
        self.controller_overlay = ControllerOverlay(self, self.cr)
        self._target = self.controller_overlay
        self.logged_in = False
        self._old_focus = None

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

    def total_nodes(self):
        return len(self.nodes._contents)

    def open_dialog(self, metadata):
        def destroy():
            self.loop.widget = self

        def ok(new_states):
            if pegasus.SINGLE_SYSTEM:
                compute, other = utils.partition(
                    lambda c: c == pegasus.NOVA_COMPUTE, new_states)
                if compute:
                    # Here we just boot the KVM, the polling process will
                    # automatically allocate new kvms to nova-compute.
                    pegasus.StartKVM().run()
                self.cr.change_allocation(other, metadata)
            else:
                self.cr.change_allocation(new_states, metadata)
            destroy()
        self.loop.widget = ChangeStateDialog(self, metadata, ok, destroy)

    def _check_login_get_data(self):
        try:
            self.logged_in = True
            return self.get_data()
        except pegasus.MaasLoginFailure:
            self.logged_in = False
            return []

    def do_update(self, data_and_juju_state):
        data, juju = data_and_juju_state
        new_data = [Node(t, self.open_dialog) for t in data]
        prev_total = len(self.nodes._contents)

        if not self.logged_in:
            self._old_focus = self.target
            self.target = TextOverlay(pegasus.MaasLoginFailure.MESSAGE, self)
        elif self._old_focus:
            self.target = self._old_focus
            self._old_focus = None

        if self.target == self.controller_overlay and \
                not self.controller_overlay.process(data):
            self.target = self
            for n in new_data:
                if n.is_horizon:
                    url = "http://{name}/horizon"
                    self.url.set_text(url.format(name=n.name))

        if pegasus.SINGLE_SYSTEM:
            # For single installs, all new 'unallocated' nodes are
            # automatically allocated to nova-compute. We process the rest of
            # the nodes normally.
            unallocated, new_data = utils.partition(
                lambda n: n.is_compute, new_data)

            for node in unallocated:
                self.cr.change_allocation([pegasus.NOVA_COMPUTE],
                                          node.metadata)

        self.nodes.update(new_data)
        self.cr.update(juju)

    def tick(self):
        if self.ticks_left == 0:
            self.ticks_left = self.poll_interval

            def update_and_redraw(data):
                self.do_update(data)
                self.loop.draw_screen()
            self.loop.run_async(self._check_login_get_data, update_and_redraw)
        self.timer.set_text("Poll in %d seconds (%d)"
                            % (self.ticks_left,
                               threading.active_count()))
        self.ticks_left = self.ticks_left - 1

    def keypress(self, size, key):
        if key == 'f5':
            self.ticks_left = 0
        if key == 'f6' and pegasus.SINGLE_SYSTEM:
            empty_metadata = {"charms": [], "units": []}
            self.open_dialog({})
        return urwid.Frame.keypress(self, size, key)


class LockScreen(urwid.Overlay):
    LOCKED = "The screen is locked. Please enter a password (this is the " \
             "password you entered for OpenStack during installation). "

    INVALID = ("error", "Invalid password.")

    IOERROR = ("error", "Problem accessing %s. Please make sure it contains "
               "exactly one line that is the lock password."
               % pegasus.PASSWORD_FILE)

    def __init__(self, underlying, unlock):
        self.unlock = unlock
        self.password = urwid.Edit("Password: ", mask='*')
        self.invalid = urwid.Text("")
        w = urwid.ListBox([urwid.Text(self.LOCKED), self.invalid,
                           self.password])
        w = urwid.LineBox(w)
        w = urwid.AttrWrap(w, "dialog")
        urwid.Overlay.__init__(self, w, underlying, 'center', 60, 'middle', 8)

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
            return urwid.Overlay.keypress(self, size, key)


class PegasusGUI(urwid.MainLoop):
    def __init__(self, get_data):
        self.console = ConsoleMode()
        self.node_view = NodeViewMode(self, get_data,
                                      self.console.command_runner)
        self.lock_ticks = 0  # start in a locked state
        self.locked = False
        urwid.MainLoop.__init__(self, self.node_view.target, STYLES,
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
            raise urwid.ExitMainLoop()

    def tick(self, unused_loop=None, unused_data=None):
        # Only lock when we are in TTY mode.
        if not self.locked and IS_TTY:
            if self.lock_ticks == 0:
                self.locked = True
                old = self.widget

                def unlock():
                    # If the controller overlay finished its work while we were
                    # locked, bypass it.
                    nonlocal old
                    if isinstance(old, ControllerOverlay) and old.done:
                        old = self.node_view
                    self.widget = old
                    self.lock_ticks = LOCK_TIME
                    self.locked = False
                self.widget = LockScreen(old, unlock)
            else:
                self.lock_ticks = self.lock_ticks - 1

        self.console.tick()
        self.node_view.tick()
        self.set_alarm_in(1.0, self.tick)

    def run(self):
        self.tick()
        with utils.console_blank():
            urwid.MainLoop.run(self)

        try:
            with open(LOG_FILE, 'a+') as f:
                f.write('----- Session closed at %s -----\n' % time())
        except IOError:
            pass

    def run_async(self, f, callback):
        """ This is a little bit goofy. The urwid API is based on select(), and
        can't actually run python functions asynchronously. So, if we want to
        run a long-running function which should update the UI, we have to get
        a fd to have urwid watch for us, and then we send data to it when it's
        done. """

        result = None

        # Here again things are a little weird: we own write_fd, but the urwid
        # API makes things a bit awkward since we end up needing mutually
        # recursive values, so we abuse python's scoping rules.
        def done(unused):
            try:
                callback(result)
            except Exception as e:
                self.console.command_runner._add("Status thread:",
                                                 format_exc())
            finally:
                self.remove_watch_pipe(write_fd)
                close(write_fd)

        write_fd = self.watch_pipe(done)

        def run_f():
            nonlocal result
            try:
                result = f()
            except Exception as e:
                self.console.command_runner._add("Status thread:",
                                                 format_exc())
            write(write_fd, bytes('done', 'ascii'))

        threading.Thread(target=run_f).start()


if __name__ == "__main__":
    def garbage(foo=[]):
        metadata = {
            "fqdn": "line %d" % len(foo),
            "cpu_count": 1,
            "memory": 2048,
            "storage": 2048,
            "id": "not a unique snowflake",
            "machine_no": 100,
            "agent_state": "pending",
        }

        if len(foo) % 2 == 1:
            metadata['charms'] = ["nova-compute"]
        if len(foo) % 3 == 1:
            metadata['charms'] = pegasus.CONTROLLER_CHARMS
        if len(foo) > 3:
            foo[0]['charms'] = ['nova-compute']
        foo.append(metadata)

        class BogusJujuState():
            services = {}
        return foo, BogusJujuState
    PegasusGUI(garbage).run()
