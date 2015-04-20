# Copyright 2015 Canonical, Ltd.
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

from urwid import (Button, Columns, Divider, LineBox, Pile,
                   WidgetWrap)

from cloudinstall.placement.controller import AssignmentType
from cloudinstall.placement.ui.services_list import ServicesList
# from cloudinstall.ui import InfoDialog
# from cloudinstall.state import CharmState

log = logging.getLogger('cloudinstall.placement')


BUTTON_SIZE = 20


class AddServicesDialog(WidgetWrap):
    """ Dialog to add services. Does not specify placement.

    :param cb: callback routine to process submit/cancel actions
    """

    def __init__(self, install_controller, deploy_cb, cancel_cb):
        self.install_controller = install_controller
        self.placement_controller = install_controller.placement_controller
        self.charms = []
        self.deploy_cb = deploy_cb
        self.cancel_cb = cancel_cb
        self.boxes = []

        w = self.build_widget()
        super().__init__(w)
        self.update()

    def build_widget(self, **kwargs):
        actions = [('Add', self.do_add)]
        self.services_list = ServicesList(self.placement_controller,
                                          actions, actions,
                                          ignore_assigned=False,
                                          ignore_deployed=True,
                                          show_placements=True)

        self.buttons = Columns([Button("Cancel", self.handle_cancel),
                                Button("Deploy", self.handle_deploy)])

        self.main_pile = Pile([self.services_list,
                               Divider(), self.buttons])
        return LineBox(self.main_pile, title="Add Services")

    def update(self):
        self.services_list.update()

    def do_add(self, sender, charm_class):
        """Add the selected charm using default juju location.
        Equivalent to a simple 'juju deploy foo'
        """
        m = self.placement_controller.def_placeholder
        self.placement_controller.assign(m, charm_class,
                                         AssignmentType.DEFAULT)
        self.update()

    def handle_deploy(self, button):
        self.deploy_cb()

    def handle_cancel(self, button):
        self.cancel_cb()
