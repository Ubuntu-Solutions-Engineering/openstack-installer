# Copyright 2014, 2015 Canonical, Ltd.
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

""" UI interface to the OpenStack Installer """

from __future__ import unicode_literals
import sys
import logging
from operator import attrgetter
import random

import urwid
from urwid import (AttrWrap, Text, Columns, Overlay, LineBox,
                   Filler, Frame, WidgetWrap, Button,
                   Pile, Divider)

from cloudinstall.task import Tasker
from cloudinstall import utils
from cloudinstall.status import get_sync_status
from cloudinstall.ui import (ScrollableWidgetWrap,
                             ScrollableListBox,
                             SelectorWithDescription,
                             PasswordInput,
                             MaasServerInput,
                             LandscapeInput,
                             InfoDialog)
from cloudinstall.notify import Event
from cloudinstall.ui.views import ErrorView
from cloudinstall.ui.utils import Color, Padding
from cloudinstall.ui.helpscreen import HelpScreen
from cloudinstall.machinewait import MachineWaitView
from cloudinstall.placement.ui import PlacementView
from cloudinstall.placement.ui.add_services_dialog import AddServicesDialog

log = logging.getLogger('cloudinstall.gui')
sys.excepthook = utils.global_exchandler

TITLE_TEXT = "Ubuntu OpenStack Installer - Dashboard"


class Banner(ScrollableWidgetWrap):

    def __init__(self):
        self.text = []
        self.flash_text = Text('', align='center')
        self.BANNER = [
            "",
            "",
            "Ubuntu OpenStack Installer",
            "",
            "By Canonical, Ltd.",
            ""
        ]
        super().__init__(self._create_text())

    def _create_text(self):
        self.text = []
        for line in self.BANNER:
            self._insert_line(line)

        self.text.append(self.flash_text)
        return ScrollableListBox(self.text)

    def _insert_line(self, line):
        text = Text(line, align='center')
        self.text.append(text)

    def flash(self, msg):
        self.flash_text.set_text([('error_major', msg)])

    def flash_reset(self):
        self.flash_text.set_text('')


class NodeInstallWaitMode(ScrollableWidgetWrap):

    def __init__(self,
                 message="Installer is initializing nodes. Please wait."):
        self.message = message
        super().__init__(self._build_node_waiting())

    def _build_node_waiting(self):
        """ creates a loading screen if nodes do not exist yet """
        text = [Text("\n\n\n"),
                Text(self.message, align="center"),
                Text("\n\n\n")]

        load_box = [AttrWrap(Text("\u2582",
                                  align="center"), "pending_icon_on"),
                    AttrWrap(Text("\u2581",
                                  align="center"),
                             "pending_icon_on"),
                    AttrWrap(Text("\u2583",
                                  align="center"), "pending_icon_on"),
                    AttrWrap(Text("\u2584",
                                  align="center"),
                             "pending_icon_on"),
                    AttrWrap(Text("\u2585",
                                  align="center"),
                             "pending_icon_on"),
                    AttrWrap(Text("\u2586",
                                  align="center"),
                             "pending_icon_on"),
                    AttrWrap(Text("\u2587",
                                  align="center"),
                             "pending_icon_on"),
                    AttrWrap(Text("\u2588",
                                  align="center"),
                             "pending_icon_on")]

        # Add loading boxes
        random.shuffle(load_box)
        loading_boxes = []
        loading_boxes.append(('weight', 1, Text('')))
        for i in load_box:
            loading_boxes.append(('pack',
                                  load_box[random.randrange(len(load_box))]))
        loading_boxes.append(('weight', 1, Text('')))
        loading_boxes = Columns(loading_boxes)

        return ScrollableListBox(text + [loading_boxes])


class ServicesView(ScrollableWidgetWrap):

    def __init__(self, nodes, juju_state, maas_state, config, **kwargs):
        nodes = [] if nodes is None else nodes
        self.juju_state = juju_state
        self.maas_state = maas_state
        self.config = config
        self.log_cache = None
        super().__init__()
        self.update(nodes)

    def update(self, nodes, **kwargs):
        self._w = self._build_widget(nodes, **kwargs)

    def _build_widget(self, nodes, **kwargs):
        unit_info = []
        for node in nodes:
            node_pile = []
            node_cols = []
            charm_class, service = node
            if len(service.units) > 0:
                for u in sorted(service.units, key=attrgetter('unit_name')):
                    node_cols = self._build_node_columns(u, charm_class)
                    node_pile.append(node_cols)

                unit_info.append(Padding.center_96(LineBox(
                    Pile(node_pile),
                    title=charm_class.display_name,
                    lline=' ',
                    blcorner=' ',
                    rline=' ',
                    bline=' ',
                    brcorner=' ')))

        return ScrollableListBox(unit_info)

    def _build_node_columns(self, unit, charm_class):
        """ builds columns of node status """
        node_cols = []

        status_txt = "{:20}".format("[{}]".format(unit.agent_state))

        # unit.agent_state may be "pending" despite errors elsewhere,
        # so we check for error_info first.
        # if the agent_state is "error", _detect_errors returns that.
        error_info = self._detect_errors(unit, charm_class)

        if error_info:
            status = ("error_icon", "\N{TETRAGRAM FOR FAILURE} ")
            if unit.agent_state != "error":
                status_txt = "{:20}".format("[{} (error)]"
                                            "".format(unit.agent_state))
        elif unit.agent_state == "pending":
            pending_status = [("pending_icon", "\N{CIRCLED BULLET} "),
                              ("pending_icon", "\N{CIRCLED WHITE BULLET} "),
                              ("pending_icon_on", "\N{FISHEYE} ")]
            status = random.choice(pending_status)
        elif unit.agent_state == "installed":
            status = ("pending_icon", "\N{HOURGLASS} ")
        elif unit.agent_state == "started":
            status = ("success_icon", "\u2713 ")
        elif unit.agent_state == "stopped":
            status = ("error_icon", "\N{BLACK FLAG} ")
        elif unit.agent_state == "down":
            status = ("error_icon", "\N{DOWNWARDS BLACK ARROW} ")
        else:
            # shouldn't get here
            status = "? "

        node_cols.append(('pack', Text([status, status_txt])))
        if unit.public_address:
            node_cols.append(
                ('pack',
                 Text("{0:<12}".format(unit.public_address))))
        elif error_info:
            node_cols.append(('pack', Text("{:<12}".format("Error"))))
        else:
            node_cols.append(
                ('pack',
                 Text("{:<12}".format("IP Pending"))))

        if error_info:
            infos = [('pack', Text(" | {}".format(error_info)))]
        else:
            hw_text = Text([" | "] + self._get_hardware_info(unit))

            if 'glance-simplestreams-sync' in unit.unit_name:
                status_oneline = get_sync_status().replace("\n", " - ")
                sync_text = Text('   ' + status_oneline)
                infos = [hw_text, sync_text]
            else:
                infos = [hw_text]

        if self.config.getopt('show_logs'):
            log_text = Text([('label',
                              self.get_log_text(unit.unit_name))])
            infos.append(log_text)

        node_cols.append(Pile(infos))

        return Columns(node_cols)

    def _get_hardware_info(self, unit):
        """Get hardware info from juju or maas

        Returns list of text and formatting tuples
        """
        juju_machine = self.juju_state.machine(unit.machine_id)
        maas_machine = None
        if self.maas_state:
            maas_machine = self.maas_state.machine(juju_machine.instance_id)

        m = juju_machine
        if juju_machine.arch == "N/A":
            if maas_machine:
                m = maas_machine
            else:
                try:
                    return self._get_container_info(unit)
                except:
                    log.exception(
                        "failed to get container info for unit {}.".format(
                            unit))

        return ["Machine {}: ".format(juju_machine.machine_id)] \
            + self._hardware_info_for_machine(m)

    def _get_container_info(self, unit):
        """Attempt to get hardware info of host machine for a unit that looks
        like a container.

        """
        base_machine = self.juju_state.base_machine(unit.machine_id)

        if base_machine.arch == "N/A" and self.maas_state is not None:
            m = self.maas_state.machine(base_machine.instance_id)
        else:
            m = base_machine

        # FIXME: Breaks single install status display
        # base_id, container_type, container_id = unit.machine_id.split('/')
        # ctypestr = dict(kvm="VM", lxc="Container")[container_type]

        # rl = ["{} {} (Machine {}".format(ctypestr, container_id,
        #                                  base_id)]
        try:
            container_id = unit.machine_id.split('/')[-1]
        except:
            log.exception("ERROR: base_machine is {} and m is {}, "
                          "and unit.machine_id is {}".format(
                              base_machine, m, unit.machine_id))
            return "?"

        base_id = base_machine.machine_id
        rl = ["Container {} (Machine {}".format(container_id,
                                                base_id)]

        if m:
            rl += [":  "] + self._hardware_info_for_machine(m) + [")"]
        else:
            rl += [")"]
        return rl

    def _hardware_info_for_machine(self, m):
        return [('label', 'arch'), ' {}  '.format(m.arch),
                ('label', 'cores'), ' {}  '.format(m.cpu_cores),
                ('label', 'mem'), ' {}  '.format(m.mem),
                ('label', 'storage'), ' {}'.format(m.storage)]

    def _detect_errors(self, unit, charm_class):
        """Look in multiple places for an error.

        Return error info string if present,
        or None if no error is found
        """
        unit_machine = self.juju_state.machine(unit.machine_id)

        if unit.agent_state == "error":
            return unit.agent_state_info.lstrip()

        err_info = ""

        if unit.agent_state == 'pending' and \
           unit_machine.agent_state is '' and \
           unit_machine.agent_state_info is not None:

            # detect MAAS API errors, returned as 409 conflict:
            if "409" in unit_machine.agent_state_info:
                if charm_class.constraints is not None:
                    err_info = "Found no machines meeting constraints: "
                    err_info += ', '.join(["{}='{}'".format(k, v) for k, v
                                           in charm_class.constraints.items()])
                else:
                    err_info += "No machines available for unit."
            else:
                err_info += unit_machine.agent_state_info
            return err_info
        return None

    def get_log_text(self, unit_name):
        name = '-'.join(unit_name.split('/'))
        cmd = ("sudo grep {unit} /var/log/juju-ubuntu-local/all-machines.log "
               " | tail -n 2")
        cmd = cmd.format(unit=name)
        out = utils.get_command_output(cmd)
        if out['status'] == 0 and len(out['output']) > 0:
            return out['output']
        else:
            return "No log matches for {}".format(name)


class Header(WidgetWrap):

    def __init__(self):
        self.title_widget = Color.frame_header(
            Padding.center_96(Text(TITLE_TEXT)))
        self.pile = Pile([self.title_widget, Text("")])
        self.set_show_add_units_hotkey(False)
        super().__init__(self.pile)

    def set_show_add_units_hotkey(self, show):
        self.show_add_units = show
        self.update()

    def update(self):
        if self.show_add_units:
            add_unit_string = '(A)dd Services \N{BULLET}'
        else:
            add_unit_string = ''
        tw = Color.frame_subheader(Text(add_unit_string + ' (H)elp \N{BULLET} '
                                        '(R)efresh \N{BULLET} (Q)uit',
                                        align='center'))
        self.pile.contents[1] = (tw, self.pile.options())


class InstallHeader(WidgetWrap):

    def __init__(self):
        w = []
        w.append(Color.frame_header(
            Text("Ubuntu Openstack Installer - Software Installation")))
        w.append(Color.frame_subheader(Text(
            '(Q)uit', align='center')))
        w = Pile(w)
        super().__init__(w)


class StatusBar(WidgetWrap):

    """Displays text."""

    INFO = "[INFO]"
    ERROR = "[ERROR]"
    ARROW = " \u21e8 "

    def __init__(self, text=''):
        self._pending_deploys = Text('')
        self._status_line = Text(text, align="center")
        self._horizon_url = Text('')
        self._jujugui_url = Text('')
        self._openstack_rel = Text('', align="right")
        self._status_extra = self._build_status_extra()
        status = Pile([self._pending_deploys,
                       self._status_extra])
        super().__init__(status)

    def _build_status_extra(self):
        col = Columns([
            ('weight', 0.3, self._horizon_url),
            ('weight', 0.3, self._jujugui_url),
            self._openstack_rel
        ], dividechars=1)
        return Color.frame_footer(Pile([
            col, self._status_line
        ]))

    def set_openstack_rel(self, text="Icehouse (2014.1.1)"):
        """ Updates openstack release text
        """
        return self._openstack_rel.set_text(text)

    def set_dashboard_url(self, ip=None, user=None, password=None):
        """ sets horizon dashboard url """
        text = "Openstack Dashboard: "
        if not ip:
            text += "(pending)"
        else:
            text += "https://{}/horizon l:{} p:{}".format(
                ip, user, password)
        return self._horizon_url.set_text(text)

    def set_jujugui_url(self, ip=None):
        """ sets juju gui url """
        text = "{0:<21}".format("JujuGUI:")
        if not ip:
            text += "(pending)"
        else:
            text += "https://{}/".format(ip)
        return self._jujugui_url.set_text(text)

    def message(self, text):
        """Write `text` on the footer."""
        self._status_line.set_text(text)

    def error_message(self, text):
        self.message([('status_error', self.ERROR),
                      self.ARROW + text])

    def info_message(self, text):
        self.message([('status_info', self.INFO),
                      self.ARROW + text])

    def set_pending_deploys(self, pending_deploys):
        if len(pending_deploys) > 0:
            msg = "Pending deploys: " + ", ".join(pending_deploys)
            self._pending_deploys.set_text(msg)
        else:
            self._pending_deploys.set_text('')

    def clear(self):
        """Clear the text."""
        self._w.set_text('')


class StepInfo(WidgetWrap):

    def __init__(self, msg=None):
        if not msg:
            msg = "Processing."
        items = [
            Padding.center_60(Text("Information", align="center")),
            Padding.center_60(
                Divider("\N{BOX DRAWINGS LIGHT HORIZONTAL}", 1, 1)),
            Padding.center_60(Text(msg))
        ]
        super().__init__(Filler(Pile(items), valign='middle'))

    def _build_buttons(self):
        buttons = [
            Padding.line_break(""),
            Color.button_secondary(
                Button("Quit", self.cancel),
                focus_map='button_secondary focus'),
        ]
        return Pile(buttons)

    def cancel(self, button):
        raise SystemExit("Installation cancelled.")


def _check_encoding():
    """Set the Urwid global byte encoding to utf-8.

    Exit the application if, for some reasons, the change does not have effect.
    """
    urwid.set_encoding('utf-8')
    if not urwid.supports_unicode():
        # Note: the following message must only include ASCII characters.
        msg = (
            'Error: your terminal does not seem to support UTF-8 encoding.\n'
            'Please check your locale settings.\n'
            'On Ubuntu, running the following might fix the problem:\n'
            '  sudo locale-gen en_US.UTF-8\n'
            '  sudo dpkg-reconfigure locales'
        )
        sys.exit(msg.encode('ascii'))


class PegasusGUI(WidgetWrap):
    key_conversion_map = {'tab': 'down', 'shift tab': 'up'}

    def __init__(self, header=None, body=None, footer=None):
        _check_encoding()  # Make sure terminal supports utf8
        cb = self.show_exception_message
        utils.register_async_exception_callback(cb)
        self.header = header if header else Header()
        self.body = body if body else Banner()
        self.footer = footer if footer else StatusBar('')

        self.frame = Frame(self.body,
                           header=self.header,
                           footer=self.footer)

        self.services_view = None
        self.placement_view = None
        self.controller = None
        self.machine_wait_view = None
        self.add_services_dialog = None
        super().__init__(self.frame)

    def keypress(self, size, key):
        key = self.key_conversion_map.get(key, key)
        return super().keypress(size, key)

    def _build_overlay_widget(self,
                              top_w,
                              align,
                              width,
                              valign,
                              height,
                              min_width,
                              min_height):
        return Overlay(top_w=Filler(top_w),
                       bottom_w=self.frame,
                       align=align,
                       width=width,
                       valign=valign,
                       height=height,
                       min_width=width,
                       min_height=height)

    def show_widget_on_top(self,
                           widget,
                           width,
                           height,
                           align='center',
                           valign='middle',
                           min_height=0,
                           min_width=0):
        """Show `widget` on top of :attr:`frame`."""
        self._w = self._build_overlay_widget(top_w=widget,
                                             align=align,
                                             width=width,
                                             valign=valign,
                                             height=height,
                                             min_width=min_width,
                                             min_height=min_height)

    def focus_next(self):
        if hasattr(self.frame.body, 'scroll_down'):
            self.frame.body.scroll_down()

    def focus_previous(self):
        if hasattr(self.frame.body, 'scroll_up'):
            self.frame.body.scroll_up()

    def focus_first(self):
        if hasattr(self.frame.body, 'scroll_top'):
            self.frame.body.scroll_top()

    def focus_last(self):
        if hasattr(self.frame.body, 'scroll_bottom'):
            self.frame.body.scroll_bottom()

    def hide_widget_on_top(self):
        """Hide the topmost widget (if any)."""
        self._w = self.frame

    def show_help_info(self):
        self.controller = self.frame.body
        self.frame.body = HelpScreen()

    def show_step_info(self, msg):
        self.frame.body = StepInfo(msg)

    def show_selector_with_desc(self, title, opts, cb):
        self.frame.body = SelectorWithDescription(title, opts, cb)

    def show_fatal_error_message(self, msg, cb):
        w = InfoDialog(msg, cb)
        self.show_widget_on_top(w, width=50, height=20)

    def show_password_input(self, title, cb):
        self.frame.body = PasswordInput(title, cb)

    def show_maas_input(self, title, cb):
        self.frame.body = MaasServerInput(title, cb)

    def show_landscape_input(self, title, cb):
        self.frame.body = LandscapeInput(title, cb)

    def set_pending_deploys(self, pending_charms):
        self.frame.footer.set_pending_deploys(pending_charms)

    def flash(self, msg):
        self.frame.body.flash("{}\N{HORIZONTAL ELLIPSIS}".format(msg))

    def flash_reset(self):
        self.frame.body.flash_reset()

    def status_message(self, text):
        self.frame.footer.message(text)
        self.frame.set_footer(self.frame.footer)

    def status_error_message(self, message):
        self.frame.footer.error_message(message)

    def status_info_message(self, message):
        self.frame.footer.info_message(
            "{}\N{HORIZONTAL ELLIPSIS}".format(message))

    def set_dashboard_url(self, ip, user, password):
        self.frame.footer.set_dashboard_url(ip, user, password)

    def set_jujugui_url(self, ip):
        self.frame.footer.set_jujugui_url(ip)

    def set_openstack_rel(self, text):
        self.frame.footer.set_openstack_rel(text)

    def clear_status(self):
        self.frame.footer = None
        self.frame.set_footer(self.frame.footer)

    def render_services_view(self, nodes, juju_state, maas_state, config,
                             **kwargs):
        if self.services_view is None:
            self.services_view = ServicesView(nodes, juju_state, maas_state,
                                              config)

        self.services_view.update(nodes)
        self.frame.set_body(self.services_view)
        self.header.set_show_add_units_hotkey(True)

    def render_node_install_wait(self, message=None, **kwargs):
        self.frame.body = NodeInstallWaitMode(message, **kwargs)
        self.frame.set_body(self.frame.body)

    def render_placement_view(self, loop, config, cb):
        """ render placement view

        :param cb: deploy callback trigger
        """
        if self.placement_view is None:
            assert self.controller is not None
            pc = self.controller.placement_controller
            self.placement_view = PlacementView(self, pc, loop,
                                                config, cb)
        self.placement_view.update()
        self.frame.body = self.placement_view

    def render_machine_wait_view(self, config):
        if self.machine_wait_view is None:
            self.machine_wait_view = MachineWaitView(
                self, self.current_installer, config)
        self.machine_wait_view.update()
        self.frame.body = self.machine_wait_view

    def render_add_services_dialog(self, deploy_cb, cancel_cb):
        def reset():
            self.add_services_dialog = None

        def cancel():
            reset()
            cancel_cb()

        def deploy():
            reset()
            deploy_cb()

        if self.add_services_dialog is None:
            self.add_services_dialog = AddServicesDialog(self.controller,
                                                         deploy_cb=deploy,
                                                         cancel_cb=cancel)
        self.add_services_dialog.update()
        self.frame.body = Filler(self.add_services_dialog)

    def show_exception_message(self, ex):
        msg = ("A fatal error has occurred: {}\n"
               "See {} for further info.".format(ex.args[0]))
        log.error(msg)
        self.frame.body = ErrorView(ex.args[0])
        Event('stop alarm')

    def select_install_type(self, install_types, cb):
        """ Dialog for selecting installation type
        """
        self.show_selector_with_desc(
            'Select the type of installation to perform',
            install_types,
            cb)

    def __repr__(self):
        return "<Ubuntu OpenStack Installer GUI Interface>"

    def tasker(self, loop, config):
        """ Interface with Tasker class

        :param loop: urwid.Mainloop
        :param dict config: config object
        """
        return Tasker(self, loop, config)

    def exit(self, loop=None):
        """ Provide exit loop helper

        :param loop: Just a placeholder, exit with urwid.
        """
        urwid.ExitMainLoop()
