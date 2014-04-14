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

    :param command: command to run
    :type command: str
    :returns: (returncode, stdout, 0)
    :rtype: tuple

    .. code::

        # Get output of juju status
        ret, out, rtime = utils.get_command_output('juju status')
    """
    cmd_env = os.environ.copy()
    # set consistent locale
    cmd_env['LC_ALL'] = 'C'
    if timeout:
        command = "timeout %ds %s" % (timeout, command)

    p = Popen(command, shell=True,
              stdout=PIPE, stderr=STDOUT,
              bufsize=-1, env=cmd_env, close_fds=True)
    stdout, stderr = p.communicate()
    return (p.returncode, stdout.decode('utf-8'), 0)


def get_network_interface(iface):
    """ Get network interface properties

    :param iface: Interface to query (ex. eth0)
    :type iface: str
    :return: interface properties or empty if none
    :rtype: dict

    .. code::

        # Get address, broadcast, and netmask of eth0
        iface = utils.get_network_interface('eth0')
    """
    (status, output, runtime) = get_command_output('ifconfig %s' % (iface,))
    line = output.split('\n')[1:2][0].lstrip()
    regex = re.compile('^inet addr:([0-9]+(?:\.[0-9]+){3})\s+Bcast:([0-9]+(?:\.[0-9]+){3})\s+Mask:([0-9]+(?:\.[0-9]+){3})')
    match = re.match(regex, line)
    if match:
        return {'address': match.group(1),
                'broadcast': match.group(2),
                'netmask': match.group(3)}
    return {}


def get_network_interfaces():
    """ Get network interfaces

    :returns: available interfaces and their properties
    :rtype: generator
    """
    (status, output, runtime) = get_command_output('ifconfig -s')
    _ifconfig = output.split('\n')[1:-1]
    for i in _ifconfig:
        name = i.split(' ')[0]
        if 'lo' not in name:
            yield {name: get_network_interface(name)}


def partition(pred, iterable):
    """ Returns tuple of allocated and unallocated systems

    :param pred: status predicate
    :type pred: function
    :param iterable: machine data
    :type iterable: list
    :returns: ([allocated], [unallocated])
    :rtype: tuple

    .. code::

        def is_allocated(d):
            allocated_states = ['started', 'pending', 'down']
            return 'charms' in d or d['agent_state'] in allocated_states
        allocated, unallocated = utils.partition(is_allocated, [{state: 'pending'}])
    """
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

    :param size: number of string characters
    :type size: int
    :param chars: range of characters (optional)
    :type chars: str

    :returns: a random string
    :rtype: str
    """
    return ''.join(random.choice(chars) for x in range(size))


def time():
    """ Time helper

    :returns: formatted current time string
    :rtype: str
    """
    return strftime('%Y-%m-%d %H:%M')
