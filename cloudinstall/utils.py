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
import fnmatch
import logging
from threading import Thread
from functools import wraps
from time import strftime
from importlib import import_module
import pkgutil

log = logging.getLogger('cloudinstall.utils')

# String with number of minutes, or None.
blank_len = None


def load_charms():
    """ Load known charm modules
    """
    import cloudinstall.charms

    charm_modules = [import_module('cloudinstall.charms.' + mname)
                     for (_, mname, _) in
                     pkgutil.iter_modules(cloudinstall.charms.__path__)]
    return charm_modules


def async(func):
    """
    Decorator for executing a function in a separate :class:`threading.Thread`.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        thread = Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        return thread.start()
    return wrapper


def get_command_output(command, timeout=300, combine_output=True):
    """ Execute command through system shell

    :param command: command to run
    :param timeout: (optional) use 'timeout' to limit time. default 300
    :param combine_output: (optional) combine stderr and stdout. default True.
    :type command: str
    :returns: {ret: returncode, stdout: stdout, stderr: stderr)
    :rtype: dict

    .. code::

        # Get output of juju status
        cmd_dict = utils.get_command_output('juju status')
    """
    cmd_env = os.environ.copy()
    # set consistent locale
    cmd_env['LC_ALL'] = 'C'
    if timeout:
        command = "timeout %ds %s" % (timeout, command)

    if combine_output:
        stderr_dest = STDOUT
    else:
        stderr_dest = PIPE

    p = Popen(command, shell=True,
              stdout=PIPE, stderr=stderr_dest,
              bufsize=-1, env=cmd_env, close_fds=True)
    stdout, stderr = p.communicate()
    if stderr:
        stderr = stderr.decode('utf-8')
    return dict(ret=p.returncode,
                stdout=stdout.decode('utf-8'),
                stderr=stderr)


def remote_cp(machine_id, src, dst):
    log.debug("Remote copying {src} to {dst} on machine {m}".format(
        src=src,
        dst=dst,
        m=machine_id))
    ret = get_command_output(
        "juju scp {src} {m}:{dst}".format(src=src, dst=dst, m=machine_id))
    log.debug("Remote copy result: {r}".format(r=ret))


def remote_run(machine_id, cmds):
    if type(cmds) is list:
        cmds = " && ".join(cmds)
    log.debug("Remote running ({cmds}) on machine {m}".format(
        m=machine_id, cmds=cmds))
    ret = get_command_output(
        "juju run --machine {m} '{cmds}'".format(m=machine_id,
                                                 cmds=cmds))
    log.debug("Remote run result: {r}".format(r=ret))
    return ret


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
    cmd = get_command_output('ifconfig %s' % (iface,))
    line = cmd['stdout'].split('\n')[1:2][0].lstrip()
    regex = re.compile('^inet addr:([0-9]+(?:\.[0-9]+){3})\s+'
                       'Bcast:([0-9]+(?:\.[0-9]+){3})\s+'
                       'Mask:([0-9]+(?:\.[0-9]+){3})')
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
    cmd = get_command_output('ifconfig -s')
    _ifconfig = cmd['sdout'].split('\n')[1:-1]
    for i in _ifconfig:
        name = i.split(' ')[0]
        if 'lo' not in name:
            yield {name: get_network_interface(name)}


def get_host_mem():
    """ Get host memory

    Mostly used as a backup if no data can be pulled from
    the normal means in Machine()
    """
    cmd = get_command_output('head -n1 /proc/meminfo')
    out = cmd['stdout'].rstrip()
    regex = re.compile('^MemTotal:\s+(\d+)\skB')
    match = re.match(regex, out)
    if match:
        mem = match.group(1)
        mem = int(mem) / 1024 / 1024 + 1
        return int(mem)
    else:
        return 0


def get_host_storage():
    """ Get host storage

    LXC doesn't report storage so we pull from host
    """
    cmd = get_command_output('df -B G --total -l --output=avail'
                             ' -x devtmpfs -x tmpfs | tail -n 1'
                             ' | tr -d "G"')
    if not cmd['ret']:
        return cmd['stdout'].lstrip()
    else:
        return 0


def get_host_cpu_cores():
    """ Get host cpu-cores

    A backup if no data can be pulled from
    Machine()
    """
    cmd = get_command_output('nproc')
    if cmd['stdout']:
        return cmd['stdout'].strip()
    else:
        return 'N/A'


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
        allocated, unallocated = utils.partition(is_allocated,
                                                 [{state: 'pending'}])
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


def find(file_pattern, top_dir, max_depth=None, path_pattern=None):
    """generator function to find files recursively. Usage:

    .. code::

        for filename in find("*.properties", "/var/log/foobar"):
            print filename
    """
    if max_depth:
        base_depth = os.path.dirname(top_dir).count(os.path.sep)
        max_depth += base_depth

    for path, dirlist, filelist in os.walk(top_dir):
        if max_depth and path.count(os.path.sep) >= max_depth:
            del dirlist[:]

        if path_pattern and not fnmatch.fnmatch(path, path_pattern):
            continue

        for name in fnmatch.filter(filelist, file_pattern):
            yield os.path.join(path, name)
