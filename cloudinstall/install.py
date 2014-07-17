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
import time
import random
from os import getenv, path

from operator import attrgetter

from cloudinstall import utils
from cloudinstall.config import Config

log = logging.getLogger('cloudinstall.install')


class InstallController:
    """ core controller for ui and juju deployments """

    def __init__(self, ui=None, opts=None):
        self.ui = ui
        self.opts = opts
        self.config = Config()

    def create_container(self, release="trusty"):
        """ creates a maas container

        :param str release: os release
        :return: 0 on success >1 on failure
        """
        out = utils.get_command_output('sudo lxc-create -t ubuntu -n maas')
        if out['ret'] == 0:
            utils.get_command_output('sudo lxc-start -n maas')
            return False
        return True

    def get_container_ip(self, name):
        """ returns container IP

        :param str name: name to filter containers
        :return: ip of container
        """
        out = utils.get_command_output('sudo lxc-ls --fancy maas')
        line = out['stdout'][:-1].split(' ')
        ip = line[2]
        return ip

    @utils.async
    def install_maas(self):
        """ Handles initial deployment of a machine """
        if self.opts.install_type == 'multi':
            self.info_message("Creating container for MAAS")
            self.create_container()

        # Step 2
        self.init_maas()

    def init_maas(self):
        """ install and configure maas """

        self.info_message("Installing MAAS and configuring")

    def header_hotkeys(self, key):
        if key in ['q', 'Q']:
            self.exit()

    def exit(self):
        raise urwid.ExitMainLoop()

    def redraw_screen(self):
        if hasattr(self, "loop"):
            try:
                self.loop.draw_screen()
            except AssertionError as message:
                logging.critical(message)

    def update_alarm(self, *args, **kwargs):
        # Do update here.
        log.debug("Updating.")
        self.update_install_status()
        self.loop.set_alarm_in(10, self.update_alarm)

    @utils.async
    def update_install_status(self):
        """ Updating node states
        """
        self.info_message("Updating status of install")

    # - Footer
    def clear_status(self):
        self.ui.clear_status()
        self.redraw_screen()

    def info_message(self, message):
        self.ui.status_info_message(message)
        self.redraw_screen()

    def main_loop(self):
        if not hasattr(self, 'loop'):
            self.loop = urwid.MainLoop(self.ui,
                                       self.config.STYLES,
                                       handle_mouse=True,
                                       unhandled_input=self.header_hotkeys)
            self.info_message("Getting this party started!")
            self.init_maas()

        self.loop.set_alarm_in(0, self.update_alarm)
        self.loop.run()

    def start(self):
        """ Starts controller processing """
        self.main_loop()
