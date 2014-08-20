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

from __future__ import unicode_literals
import logging
import os

from logging.handlers import TimedRotatingFileHandler


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

    .. note::

        This filters only cloudinstall logging info. Set your environment
        var to `UCI_NOFILTER` to see debugging log statements from imported
        libraries (ie macumba)

    .. code::

        # Running cloud-status from cli
        $ UCI_LOGLEVEL=INFO cloud-status

        # Disable log filtering
        $ UCI_NOFILTER=1 cloud-status

    :params str name: logger name
    :returns: a log object

    """
    HOME = os.getenv('HOME')
    CONFIG_DIR = '.cloud-install'
    CONFIG_PATH = os.path.join(HOME, CONFIG_DIR)
    if not os.path.isdir(CONFIG_PATH):
        os.makedirs(CONFIG_PATH)
    LOGFILE = os.path.join(CONFIG_PATH, 'commands.log')
    commandslog = TimedRotatingFileHandler(LOGFILE,
                                           when='D',
                                           interval=1,
                                           backupCount=7)
    commandslog.setFormatter(logging.Formatter(
        '%(levelname)s \N{BULLET} %(asctime)s [LINE:%(lineno)d] '
        '\N{BULLET} %(name)s \N{BULLET} '
        '%(message)s',
        datefmt='%m-%d %H:%M:%S'))

    logger = logging.getLogger('')
    env = os.environ.get('UCI_LOGLEVEL', 'DEBUG')
    no_filter = os.environ.get('UCI_NOFILTER', None)
    if not no_filter:
        f = logging.Filter(name='cloudinstall')
        commandslog.addFilter(f)
    logger.setLevel(env)
    logger.addHandler(commandslog)

    return logger
