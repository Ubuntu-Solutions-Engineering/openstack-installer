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

from urwid import (AttrWrap, Button, BoxAdapter, Columns, Divider, IntEdit,
                   LineBox, ListBox, RadioButton, SimpleListWalker, WidgetWrap)

# from cloudinstall.placement.ui.machine_chooser import MachineChooser
# from cloudinstall.placement.ui.machines_list import MachinesList
# from cloudinstall.placement.ui.service_chooser import ServiceChooser
# from cloudinstall.placement.ui.services_list import ServicesList
# from cloudinstall.ui import InfoDialog
# from cloudinstall.state import CharmState

log = logging.getLogger('cloudinstall.placement')


BUTTON_SIZE = 20


class AddServicesDialog(WidgetWrap):

    """ Adding charm dialog

    :param cb: callback routine to process submit/cancel actions
    :returns: input from dialog
    """

    def __init__(self, cb, **kwargs):
        self.charms = []
        self.cb = cb
        self.count_editor = None
        self.boxes = []

        w = self.build_widget()
        w = AttrWrap(w, "dialog")

        super().__init__(w)

    def do_deploy(self):
        self.cb()  # TODO

    def cancel(self):
        """ Handle cancel action """
        self.cb()  # TODO

    def build_widget(self, **kwargs):

        num_of_items, charm_sel = self._insert_charm_selections()

        # Control buttons
        buttons = self._insert_buttons()

        return LineBox(
            BoxAdapter(
                ListBox([charm_sel, Divider(), buttons]),
                height=num_of_items + 2),
            title="Add unit")

    def _insert_charm_selections(self):
        first_index = 0
        bgroup = []
        for i, charm_class in enumerate(self.charms):
            charm = charm_class
            if charm.name() and not first_index:
                first_index = i
            r = RadioButton(bgroup, charm.name())
            r.text_label = charm.name()
            self.boxes.append(r)

        # Add input widget for specifying NumUnits
        self.count_editor = IntEdit("Number of units to add: ", 1)
        self.boxes.append(self.count_editor)
        wrapped_boxes = self._wrap_focus(self.boxes)
        items = ListBox(SimpleListWalker(wrapped_boxes))
        items.set_focus(first_index)
        return (len(self.boxes), BoxAdapter(items, len(self.boxes)))

    def _insert_buttons(self):
        bs = [Button("Ok", self.yes), Button("Cancel", self.no)]
        wrapped_buttons = self._wrap_focus(bs)
        return Columns(wrapped_buttons)

    def yes(self, button):
        self.submit()

    def no(self, button):
        self.cancel()

    def _wrap_focus(self, widgets, unfocused=None):
        try:
            return [AttrWrap(w, "focus", 'radio focus') for w in widgets]
        except TypeError:
            return AttrWrap(widgets, "focus", 'radio focus')
