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
import logging.handlers
import os

def logger(name='ubuntu-cloud-installer'):
    """ setup logging

    Overridding the default log level(**debug**) can be done via an environment variable `UCI_LOGLEVEL`

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
    LOGFILE = os.path.expanduser('~/.cloud-install/commands.log')
    commandslog = logging.FileHandler(LOGFILE, 'w')
    commandslog.setFormatter(logging.Formatter(
        '%(asctime)s %(pathname)s [%(process)d] * ' \
        '%(levelname)s %(name)s - %(message)s'))

    syslog = logging.handlers.SysLogHandler(address='/dev/log')
    syslog.setLevel(logging.WARNING)
    syslog.setFormatter(logging.Formatter(
        '%(pathname)s [%(process)d]: %(levelname)s %(message)s'))

    logger = logging.getLogger(name)
    env = os.environ.get('UCI_LOGLEVEL', 'DEBUG')
    logger.setLevel(env)
    logger.addHandler(commandslog)
    logger.addHandler(syslog)

    return logger
