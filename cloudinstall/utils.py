#
# utils.py - Helper utilies for cloud installer
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

from subprocess import Popen, PIPE, DEVNULL, call, STDOUT
from contextlib import contextmanager
import os
import re
import string
import random

# String with number of minutes, or None.
blank_len = None


def get_command_output(command, timeout=300):
    """ Execute command through system shell

    @return: returncode, stdout, 0
    """
    cmd_env = os.environ
    # set consistent locale
    cmd_env['LC_ALL'] = 'C'
    if timeout:
        command = "/usr/bin/timeout %ds %s" % (timeout, command)

    p = Popen(command, shell=True,
              stdout=PIPE, stderr=STDOUT,
              bufsize=-1, env=cmd_env, close_fds=True)
    stdout, stderr = p.communicate()
    return (p.returncode, stdout.decode('utf-8'), 0)


def get_network_interface(iface):
    """ Get network interface properties

    @param iface: Interface to query (ex. eth0)
    @return: dict of interface properties or None if no properties
    """
    (status, output, runtime) = get_command_output('ifconfig %s' % (iface,))
    line = output.split('\n')[1:2][0].lstrip()
    regex = re.compile('^inet addr:([0-9]+(?:\.[0-9]+){3})\s+Bcast:([0-9]+(?:\.[0-9]+){3})\s+Mask:([0-9]+(?:\.[0-9]+){3})')
    match = re.match(regex, line)
    if match:
        return {'address': match.group(1),
                'broadcast': match.group(2),
                'netmask': match.group(3)}
    return None


def get_network_interfaces():
    """ Get network interfaces

    @return: list of available interfaces and their properties
    """
    interfaces = []
    (status, output, runtime) = get_command_output('ifconfig -s')
    _ifconfig = output.split('\n')[1:-1]
    for i in _ifconfig:
        name = i.split(' ')[0]
        if 'lo' not in name:
            interfaces.append({name: get_network_interface(name)})
    return interfaces


def partition(pred, iterable):
    yes, no = [], []
    for i in iterable:
        (yes if pred(i) else no).append(i)
    return (yes, no)


# TODO: replace with check_output()
def _run(cmd):
    return Popen(cmd.split(), stdout=PIPE, stderr=DEVNULL).communicate()[0]


def reset_blanking():
    global blank_len
    if blank_len is not None:
        call(('setterm', '-blank', blank_len))


@contextmanager
def console_blank():
    global blank_len
    try:
        with open('/sys/module/kernel/parameters/consoleblank') as f:
            blank_len = f.read()
    except (IOError, FileNotFoundError):
        blank_len = None
    else:
        # Cannot use anything that captures stdout, because it is needed
        # by the setterm command to write to the console.
        call(('setterm', '-blank', '0'))
        # Convert the interval from seconds to minutes.
        blank_len = str(int(blank_len)//60)

    yield

    reset_blanking()


def randomString(size=6, chars=string.ascii_uppercase + string.digits):
    """ Generate a random string

    @param size: number of string characters
    @param chars: range of characters (optional)

    @return: a random string
    """
    return ''.join(random.choice(chars) for x in range(size))
