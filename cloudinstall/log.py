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
"""

import logging
import os


def setup_logger(name=__name__):
    """setup logging

    Overridding the default log level(**debug**) can be done via an
    environment variable `UCI_LOGLEVEL`

    Available levels:

    * CRITICAL
    * ERROR
    * WARNING
    * INFO
    * DEBUG

    .. code::

        # Running cloud-status from cli
        $ UCI_LOGLEVEL=INFO cloud-status

    :params str name: logger name
    :returns: a log object

    """
    HOME = os.getenv('HOME')
    CONFIG_DIR = '.cloud-install'
    CONFIG_PATH = os.path.join(HOME, CONFIG_DIR)
    LOGFILE = os.path.join(CONFIG_PATH, 'commands.log')
    commandslog = logging.FileHandler(LOGFILE, 'w')
    commandslog.setFormatter(logging.Formatter(
        '%(levelname)-9s * %(asctime)s [PID:%(process)d] * %(name)s * '
        '%(message)s',
        datefmt='%m-%d %H:%M:%S'))

    logger = logging.getLogger('')
    env = os.environ.get('UCI_LOGLEVEL', 'DEBUG')
    logger.setLevel(env)
    logger.addHandler(commandslog)

    return logger
log = setup_logger()
