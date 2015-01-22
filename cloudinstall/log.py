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
import pprint

from logging.handlers import TimedRotatingFileHandler


class PrettyLog():

    def __init__(self, obj):
        self.obj = obj

    def __repr__(self):
        return pprint.pformat(self.obj)


def setup_logger(name=__name__, headless=False):
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
        $ UCI_LOGLEVEL=INFO openstack-status

        # Disable log filtering
        $ UCI_NOFILTER=1 openstack-status

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
    env = os.environ.get('UCI_LOGLEVEL', 'DEBUG')

    commandslog.setLevel(env)
    commandslog.setFormatter(logging.Formatter(
        "[%(levelname)-5s \N{BULLET} %(asctime)s] "
        "\N{BULLET} %(name)s \N{BULLET} "
        "(%(filename)s, %(funcName)s, %(lineno)d)]\n"
        "   %(message)s",
        datefmt='%m-%d %H:%M:%S'))

    if headless:
        consolelog = logging.StreamHandler()
        consolelog.setLevel(logging.INFO)
        consolelog.setFormatter(logging.Formatter(
            '[%(levelname)-5s \N{BULLET} %(asctime)s \N{BULLET} %(name)-16s] '
            '%(message)s',
            datefmt='%m-%d %H:%M:%S'))

    logger = logging.getLogger('')
    logger.setLevel(env)

    no_filter = os.environ.get('UCI_NOFILTER', None)
    if no_filter is None:
        f = logging.Filter(name='cloudinstall')
        commandslog.addFilter(f)
        if headless:
            consolelog.addFilter(f)
    logger.addHandler(commandslog)
    if headless:
        logger.addHandler(consolelog)

    return logger
