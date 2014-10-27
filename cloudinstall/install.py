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

from cloudinstall.core import DisplayController
from cloudinstall.single_install import SingleInstall
from cloudinstall.landscape_install import LandscapeInstall
from cloudinstall.multi_install import (MultiInstallNewMaas,
                                        MultiInstallExistingMaas)


log = logging.getLogger('cloudinstall.install')


class InstallController(DisplayController):

    """ Install controller """

    def __init__(self, **kwds):
        super().__init__(**kwds)

    def _save_password(self, password=None, confirm_pass=None):
        """ Checks passwords match and proceeds
        """
        if password.value and \
           password.value == confirm_pass.value:
            self.config.save_password(password.value)
            self.ui.hide_show_password_input()
            self.select_install_type()
        else:
            self.error_message('Passwords did not match, try again ..')
            return self.show_password_input(
                'Openstack Password', self._save_password)

    def select_install_type(self):
        """ Dialog for selecting installation type
        """
        self.info_message("Choose your installation path ..")
        self.show_selector_info('Install Type',
                                self.config.install_types,
                                self.do_install)

    def main_loop(self):
        if not hasattr(self, 'loop'):
            self.loop = urwid.MainLoop(self.ui,
                                       self.config.STYLES,
                                       handle_mouse=True,
                                       unhandled_input=self.header_hotkeys)

        self.info_message("Get started by entering an Openstack password "
                          "to use in your cloud ..")
        self.render_node_install_wait(message="Starting install")

        self.ui.show_password_input(
            'Openstack Password', self._save_password)
        self.update_alarm()
        self.loop.run()

    def update_alarm(self, *args, **kwargs):
        interval = 1
        self.render_node_install_wait()
        self.loop.set_alarm_in(interval, self.update_alarm)

    def do_install(self, install_type):
        """ Callback for install type selector
        """
        self.ui.hide_selector_info()
        if 'Single' in install_type:
            SingleInstall(self.opts, self).run()
        elif 'Multi with existing MAAS' == install_type:
            MultiInstallExistingMaas(self.opts, self).run()
        elif 'Multi' == install_type:
            MultiInstallNewMaas(self.opts, self).run()
        else:
            LandscapeInstall(self.opts, self).run()
