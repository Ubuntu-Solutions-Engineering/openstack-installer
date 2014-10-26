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

from subprocess import (Popen, PIPE, call, STDOUT, check_output,
                        CalledProcessError)
from contextlib import contextmanager
from collections import deque
from jinja2 import Environment, FileSystemLoader
import os
import re
import string
import random
import fnmatch
import logging
import traceback
from threading import Thread
from functools import wraps
import time
from importlib import import_module
import pkgutil
import sys
import errno
import shlex
import shutil

log = logging.getLogger('cloudinstall.utils')

# String with number of minutes, or None.
blank_len = None


def global_exchandler(type, value, tb):
    """ helper routine capturing tracebacks and printing to log file """
    tb_list = traceback.format_exception(type, value, tb)
    log.debug("".join(tb_list))

    locals = True
    for active_vars in [tb.tb_frame.f_locals, tb.tb_frame.f_globals]:
        header = 'Locals:' if locals else 'Globals:'
        log.debug(header)
        for k, v in active_vars.items():
            if not (k.startswith('__') and k.endswith('__')):
                log.debug('\t{} = {}'.format(k, v))
        locals = False


class ExceptionLoggingThread(Thread):

    def run(self):
        try:
            super().run()
        except Exception:
            global_exchandler(*sys.exc_info())


class UtilsException(Exception):
    pass


def load_charms():
    """ Load known charm modules
    """
    import cloudinstall.charms

    charm_modules = [import_module('cloudinstall.charms.' + mname)
                     for (_, mname, _) in
                     pkgutil.iter_modules(cloudinstall.charms.__path__)]
    return charm_modules


def load_charm_byname(name):
    """ Load a charm by name

    :param str name: name of charm
    """
    return import_module('cloudinstall.charms.{}'.format(name))


def chown(path, user, group, recursive=False):
    """
    Change user/group ownership of file

    :param path: path of file or directory
    :param str user: new owner username
    :param str group: new owner group name
    :param bool recursive: set files/dirs recursively

    """
    try:
        if not recursive or os.path.isfile(path):
            shutil.chown(path, user, group)
        else:
            for root, dirs, files in os.walk(path):
                for item in dirs:
                    shutil.chown(os.path.join(root, item), user, group)
                for item in files:
                    shutil.chown(os.path.join(root, item), user, group)
    except OSError as e:
        raise UtilsException(e)


def async(func):
    """
    Decorator for executing a function in a separate thread.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        thread = ExceptionLoggingThread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        return thread.start()
    return wrapper


def get_command_output(command, timeout=300, user_sudo=False):
    """ Execute command through system shell

    :param command: command to run
    :param timeout: (optional) use 'timeout' to limit time. default 300
    :param user_sudo: (optional) sudo into install users env. default False.
    :type command: str
    :returns: {status: returncode, output: stdout+stdeer}
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

    if user_sudo:
        command = "sudo -H -u {0} {1}".format(install_user(), command)

    try:
        p = Popen(command, shell=True,
                  stdout=PIPE, stderr=STDOUT,
                  bufsize=-1, env=cmd_env, close_fds=True)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return dict(ret=127, output="")
        else:
            raise e
    stdout, stderr = p.communicate()
    if p.returncode == 126 or p.returncode == 127:
        stdout = bytes()
    return dict(status=p.returncode,
                output=stdout.decode('utf-8'))


def poll_until_true(cmd, predicate, frequency, timeout=600,
                    ignore_exceptions=False):
    """run get_command_output(cmd) every frequency seconds, until
    predicate(output) returns True. Timeout after timeout seconds.

    returns True if call eventually succeeded, or False if timeout was
    reached.

    Exceptions raised during get_command_output are handled as per
    ignore_exceptions. If True, they are just logged. If False, they
    are re-raised.

    """
    start_time = time.time()
    frequency_stub = time.time()
    while True:
        # continue if frequency not met
        if time.time() - frequency_stub <= frequency:
            continue
        try:
            output = get_command_output(cmd)
        except Exception as e:
            if not ignore_exceptions:
                raise e
            else:
                log.debug("**Ignoring** exception: {}".format(e))
        if predicate(output):
            return True
        if time.time() - start_time >= timeout:
            return False


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


def get_host_mem():
    """ Get host memory

    Mostly used as a backup if no data can be pulled from
    the normal means in Machine()
    """
    cmd = get_command_output('head -n1 /proc/meminfo')
    out = cmd['output'].rstrip()
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
    if not cmd['status']:
        return cmd['output'].lstrip()
    else:
        return 0


def get_host_cpu_cores():
    """ Get host cpu-cores

    A backup if no data can be pulled from
    Machine()
    """
    cmd = get_command_output('nproc')
    if cmd['output']:
        return cmd['output'].strip()
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
    return Popen(cmd.split(), stdout=PIPE, stderr=STDOUT).communicate()[0]


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
    except (IOError, FileNotFoundError):  # NOQA
        blank_len = None
    else:
        # Cannot use anything that captures stdout, because it is needed
        # by the setterm command to write to the console.
        call(('setterm', '-blank', '0'))
        # Convert the interval from seconds to minutes.
        blank_len = str(int(blank_len) // 60)

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


def random_password(size=32):
    """ Generate a password

    :param int size: length of password
    """
    out = get_command_output("pwgen -s {}".format(size))
    return out['output'].strip()


def time_string():
    """ Time helper

    :returns: formatted current time string
    :rtype: str
    """
    return time.strftime('%Y-%m-%d %H:%M')


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


def container_ip(name):
    """ gets container ip of named container
    """
    for filename in find('*.leases', '/var/lib/misc'):
        with open(filename, 'r') as f:
            for line in f.readlines():
                if name in line:
                    return line.split()[-3]
    return None


def container_run(name, cmd):
    """ run command in container

    :param str name: name of container
    :param str cmd: command to run
    """
    ip = container_ip(name)
    cmd = "sudo -H -u {3} TERM=xterm256-color ssh -t -q " \
          "-l ubuntu -o \"StrictHostKeyChecking=no\" " \
          "-o \"UserKnownHostsFile=/dev/null\" " \
          "-i {2} " \
          "{0} {1}".format(ip, cmd, ssh_privkey(), install_user())
    log.debug("Running in container: {0}".format(cmd))
    # ret = os.system("{0} >>/dev/null".format(cmd))
    try:
        ret = check_output(cmd, stderr=STDOUT, shell=True)
        log.debug(ret)
    except CalledProcessError as e:
        raise SystemExit("There was a problem running ({0}) in the container "
                         "({1}:{2}) Error: {3}".format(cmd, name, ip, e))


def container_run_status(name, cmd):
    """ Runs cloud-status in container
    """
    ip = container_ip(name)
    cmd = "sudo -H -u {2} TERM=xterm256-color ssh -t -q " \
          "-l ubuntu -o \"StrictHostKeyChecking=no\" " \
          "-o \"UserKnownHostsFile=/dev/null\" " \
          "-i {1} " \
          "{0} {3}".format(ip, ssh_privkey(), install_user(), cmd)
    log.debug("Running command without waiting for response.")
    args = deque(shlex.split(cmd))
    os.execlp(args.popleft(), *args)


def container_cp(name, filepath, dst):
    """ copy file to container

    :param str name: name of container
    :param str filepath: file to copy to cintainer
    :param str dst: destination of remote path
    """
    ip = container_ip(name)
    cmd = "scp -r -q " \
          "-o \"StrictHostKeyChecking=no\" " \
          "-o \"UserKnownHostsFile=/dev/null\" " \
          "-i {identity} " \
          "{filepath} " \
          "ubuntu@{ip}:{dst} >>/dev/null".format(ip=ip, dst=dst,
                                                 identity=ssh_privkey(),
                                                 filepath=filepath)
    ret = os.system(cmd)
    if ret > 0:
        raise SystemExit("There was a problem copying ({0}) to the container "
                         "({1}:{2})".format(filepath, name, ip))
    return


def container_create(name, userdata):
    """ creates a container from ubuntu-cloud template
    """
    out = get_command_output(
        'sudo lxc-create -t ubuntu-cloud '
        '-n {0} -- -u {1}'.format(name, userdata))
    if out['status'] > 0:
        raise SystemExit("Unable to create container: "
                         "{0}".format(out['output']))
    return out['status']


def container_start(name):
    """ starts lxc container

    :param str name: name of container
    """
    out = get_command_output(
        'sudo lxc-start -n {0} -d'.format(name))

    if out['status'] > 0:
        raise SystemExit("Unable to start container: "
                         "{0}".format(out['output']))
    return out['status']


def container_stop(name):
    """ stops lxc container

    :param str name: name of container
    """
    out = get_command_output(
        'sudo lxc-stop -n {0}'.format(name))

    if out['status'] > 0:
        raise SystemExit("Unable to stop container: "
                         "{0}".format(out['output']))

    return out['status']


def container_destroy(name):
    """ destroys lxc container

    :param str name: name of container
    """
    out = get_command_output(
        'sudo lxc-destroy -n {0}'.format(name))

    if out['status'] > 0:
        raise SystemExit("Unable to destroy container: "
                         "{0}".format(out['output']))

    return out['status']


def container_wait(name):
    """ waits for the container to be in a RUNNING state

    :param str name: name of container
    """
    out = get_command_output(
        'sudo lxc-wait -n {0} -s RUNNING'.format(name))
    return out['status']


def load_template(name):
    """ load template file

    :param str name: name of template file
    """
    env = Environment(
        loader=FileSystemLoader('/usr/share/openstack/templates'))
    return env.get_template(name)


def install_user():
    """ returns sudo user
    """
    user = os.getenv('SUDO_USER', None)
    if not user:
        user = os.getenv('USER', 'root')
    return user


def install_home():
    """ returns installer user home
    """
    return os.path.join('/home', install_user())


def ssh_readkey():
    """ reads ssh key
    """
    with open(ssh_pubkey(), 'r') as f:
        return f.read()


def ssh_genkey():
    """ Generates sshkey
    """
    if not os.path.exists(ssh_privkey()):
        user_sshkey_path = os.path.join(install_home(), '.ssh/id_rsa')
        cmd = "ssh-keygen -N '' -f {0}".format(user_sshkey_path)
        out = get_command_output(cmd, user_sudo=True)
        if out['status'] != 0:
            print("Unable to generate key: {0}".format(out['stderr']))
            sys.exit(out['ret'])
        get_command_output('sudo chown -R {0}:{0} {1}'.format(
            install_user(), os.path.join(install_home(), '.ssh')))
        get_command_output('chmod 600 {0}.pub'.format(user_sshkey_path),
                           user_sudo=True)
    else:
        log.debug(
            '*** ssh keys exist for this user, they will be used instead'
            '*** If the current ssh keys are not passwordless you\'ll be'
            '*** required to enter your ssh key password during container'
            '*** creation.')


def ssh_pubkey():
    """ returns path of ssh public key
    """
    return os.path.join(install_home(), '.ssh/id_rsa.pub')


def ssh_privkey():
    """ returns path of private key
    """
    return os.path.join(install_home(), '.ssh/id_rsa')


def spew(path, data, owner=None):
    """ Writes data to path

    :param str path: path of file to write to
    :param str data: contents to write
    :param str owner: optional owner of file
    """
    with open(path, 'w') as f:
        f.write(data)
    if owner:
        get_command_output("chown {0}:{0}".format(owner))


def slurp(path):
    """ Reads data from path

    :param str path: path of file
    """
    try:
        with open(path) as f:
            return f.read().strip()
    except IOError:
        raise IOError
