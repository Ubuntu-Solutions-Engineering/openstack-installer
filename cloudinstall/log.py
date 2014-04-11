#
# log.py - Logger
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

""" Logging interface

Simply exports `logger` variable
"""

import logging
from os.path import expanduser, isfile

LOG_FILE = "~/.cloud-install/commands.log"
if isfile(LOG_FILE):
    LOG_FILE = expanduser(LOG_FILE)
    logging.basicConfig(filename=LOG_FILE, filemode='w',
                        level=logging.DEBUG, datefmt='%m-%d %H:%M',
                        format='%(asctime)s * %(name)s - %(message)s')

logger = logging
