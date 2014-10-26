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

""" re-usable input widgets """

from urwid import (Edit, WidgetWrap)

import logging

log = logging.getLogger('cloudinstall.ui.input')


class EditInput(WidgetWrap):

    """ Edit input class

    Initializes an Edit object and attaches its result to
    the `value` accessor.
    """

    def __init__(self, caption, **kwargs):
        self._edit = Edit(caption=caption, **kwargs)
        super().__init__(self._edit)

    @property
    def value(self):
        """ Returns text of input
        """
        return self._edit.get_edit_text()
