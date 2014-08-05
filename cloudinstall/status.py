#
# status.py - rabbitmq-based distributed status info receiver
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

import atexit
import logging
import os
import subprocess

SYNC_STATUS_LISTENER_PATH = "/usr/share/cloud-installer/bin/status-listener"
STATUS_FILE_NAME = os.path.expanduser("~/.cloud-install/sync-status")

status_subprocess = None

log = logging.getLogger('cloudinstall.status')


def get_sync_status():
    global status_subprocess
    if status_subprocess is None:
        status_listener_path = os.environ.get("SYNC_STATUS_LISTENER_PATH",
                                              SYNC_STATUS_LISTENER_PATH)
        log.debug('starting status listener {}'.format(status_listener_path))
        try:
            status_subprocess = subprocess.Popen([status_listener_path])
            atexit.register(status_subprocess.kill)
        except OSError:
            log.exception("Error starting status listener")
            status_subprocess = None

    if os.path.exists(STATUS_FILE_NAME):
        with open(STATUS_FILE_NAME) as sf:
            status = sf.read()
        log.debug("got status '{}' from listener file".format(status))
        return status
    else:
        log.debug("No status file found, returning empty status.")
        return ""
