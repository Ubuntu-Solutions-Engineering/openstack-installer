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
import logging

import urwid
from urwid import (Text, Pile,
                   Filler, Frame, WidgetWrap)

from cloudinstall.task import Tasker
from cloudinstall.ui.widgets import (SelectorWithDescriptionWidget,
                                     PasswordInput,
                                     MaasServerInput,
                                     LandscapeInput,
                                     StatusBarWidget)
from cloudinstall.alarms import AlarmMonitor
from cloudinstall.ui.views import (ErrorView,
                                   ServicesView,
                                   MachineWaitView,
                                   HelpView,
                                   NodeInstallWaitView,
                                   StepInfoView)
from cloudinstall.ui.utils import Color
from cloudinstall.placement.ui import PlacementView
from cloudinstall.placement.ui.add_services_dialog import AddServicesDialog

log = logging.getLogger('cloudinstall.gui')


class Banner(WidgetWrap):

    def __init__(self):
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
        text = []
        for line in self.BANNER:
            text.append(Text(line, align='center'))
        return Pile(text)


class Header(WidgetWrap):

    TITLE_TEXT = "Ubuntu OpenStack Installer - Dashboard"

    def __init__(self):
        self.text = Text(self.TITLE_TEXT)
        self.widget = Color.frame_header(self.text)
        self.pile = Pile([self.widget, Text("")])
        self.set_show_add_units_hotkey(False)
        super().__init__(self.pile)

    def set_openstack_rel(self, release):
        self.text.set_text("{} ({})".format(self.TITLE_TEXT, release))

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

    TITLE_TEXT = "Ubuntu Openstack Installer - Software Installation"

    def __init__(self):
        self.text = Text(self.TITLE_TEXT)
        self.widget = Color.frame_header(self.text)
        w = [
            Color.frame_header(self.widget),
            Color.frame_subheader(Text(
                '(Q)uit', align='center'))
        ]
        super().__init__(Pile(w))

    def set_openstack_rel(self, release):
        self.text.set_text("{} ({})".format(
            self.TITLE_TEXT, release))


class PegasusGUI(WidgetWrap):
    key_conversion_map = {'tab': 'down', 'shift tab': 'up'}

    def __init__(self, header=None, body=None, footer=None):
        self.header = header if header else Header()
        self.body = body if body else Banner()
        self.footer = footer if footer else StatusBarWidget()

        self.frame = Frame(self.body,
                           header=self.header,
                           footer=self.footer)

        self.services_view = None
        self.placement_view = None
        self.controller = None
        self.machine_wait_view = None
        self.node_install_wait_view = None
        self.add_services_dialog = None
        super().__init__(self.frame)

    def keypress(self, size, key):
        key = self.key_conversion_map.get(key, key)
        return super().keypress(size, key)

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

    def show_help_info(self):
        self.controller = self.frame.body
        self.frame.body = HelpView()

    def show_step_info(self, msg):
        self.frame.body = StepInfoView(msg)

    def show_selector_with_desc(self, title, opts, cb):
        self.frame.body = SelectorWithDescriptionWidget(title, opts, cb)

    def show_password_input(self, title, cb):
        self.frame.body = PasswordInput(title, cb)

    def show_maas_input(self, title, cb):
        self.frame.body = MaasServerInput(title, cb)

    def show_landscape_input(self, title, cb):
        self.frame.body = LandscapeInput(title, cb)

    def set_pending_deploys(self, pending_charms):
        self.frame.footer.set_pending_deploys(pending_charms)

    def status_message(self, text):
        self.frame.footer.message(text)
        self.frame.set_footer(self.frame.footer)

    def status_error_message(self, message):
        self.frame.footer.error_message(message)

    def status_info_message(self, message):
        self.frame.footer.info_message(
            "{}\N{HORIZONTAL ELLIPSIS}".format(message))

    def set_openstack_rel(self, release):
        self.frame.header.set_openstack_rel(release)

    def clear_status(self):
        self.frame.footer = None
        self.frame.set_footer(self.frame.footer)

    def render_services_view(self, nodes, juju_state, maas_state, config):
        self.services_view = ServicesView(nodes, juju_state, maas_state,
                                          config)
        self.frame.body = self.services_view
        self.header.set_show_add_units_hotkey(True)
        self.update_phase_status(config)

    def refresh_services_view(self, nodes, config):
        self.services_view.refresh_nodes(nodes)
        self.update_phase_status(config)

    def update_phase_status(self, config):
        dc = config.getopt('deploy_complete')
        dcstr = "complete" if dc else "pending"
        rc = config.getopt('relations_complete')
        rcstr = "complete" if rc else "pending"
        ppc = config.getopt('postproc_complete')
        ppcstr = "complete" if ppc else "pending"
        self.status_info_message("Status: Deployments {}, "
                                 "Relations {}, "
                                 "Post-processing {} ".format(dcstr,
                                                              rcstr,
                                                              ppcstr))

    def render_node_install_wait(self, message):
        if self.node_install_wait_view is None:
            self.node_install_wait_view = NodeInstallWaitView(message)
        self.frame.body = self.node_install_wait_view

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
        msg = ("A fatal error has occurred: {}\n".format(ex.args[0]))
        log.error(msg)
        self.frame.body = ErrorView(ex.args[0])
        AlarmMonitor.remove_all()

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
