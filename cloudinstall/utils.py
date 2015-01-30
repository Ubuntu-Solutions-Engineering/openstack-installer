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
                        check_call, DEVNULL, CalledProcessError)
from contextlib import contextmanager
from collections import deque
try:
    from collections import Mapping
except ImportError:
    Mapping = dict

from jinja2 import Environment, FileSystemLoader
import os
import re
import string
import random
import fnmatch
import logging
import traceback
import urwid
import itertools
import configparser
from threading import Thread
from functools import wraps
import time
from importlib import import_module
import pkgutil
import platform
import sys
import errno
import shlex
import shutil
import subprocess
import json
import yaml

log = logging.getLogger('cloudinstall.utils')

# String with number of minutes, or None.
blank_len = None


def global_exchandler(type, value, tb):
    """ helper routine capturing tracebacks and printing to log file """
    tb_list = traceback.format_exception(type, value, tb)
    log.debug("".join(tb_list))


_async_exception_callback = None


def register_async_exception_callback(cb):
    global _async_exception_callback
    _async_exception_callback = cb


class ExceptionLoggingThread(Thread):

    def run(self):
        try:
            super().run()
        except Exception as e:
            global_exchandler(*sys.exc_info())
            if _async_exception_callback:
                _async_exception_callback(e)


class UtilsException(Exception):
    pass


def cleanup(cfg):
    # Save latest config object
    log.info("Cleanup, saving latest config object.")
    cfg.save()
    pid = os.path.join(install_home(), '.cloud-install/openstack.pid')
    if os.path.isfile(pid):
        os.remove(pid)
    if not cfg.getopt('headless'):
        log.debug('Attempting to reset the terminal')
        sys.stderr.write("\x1b[2J\x1b[H")
        call(['stty', 'sane'])
    return


def write_status_file(status='', msg=''):
    """ Writes out a status file

    :param str status: success or fail
    :param str msg: any error/success output
    """
    status_file = os.path.join(install_home(), '.cloud-install/finished.json')
    spew(status_file, json.dumps(dict(status=status, msg=msg)))


def populate_config(opts):
    """ populate configuration suitable for loading in the config
    object merging in cli options.

    :param opts: argparse Namespace class of options
    """
    cfg_cli_opts = vars(opts)
    cfg = {}

    def sanitize_config_items(_cfg):
        """ remove false and null items """
        return {k: v for (k, v) in _cfg.items()
                if v is not None}

    if 'config_file' not in cfg_cli_opts:
        # Check for a pre-existing install config
        presaved_config = os.path.join(
            install_home(), '.cloud-install/config.yaml')
        if os.path.exists(presaved_config):
            cfg.update(yaml.load(slurp(presaved_config)))
        scrub = sanitize_config_items(cfg_cli_opts)
        cfg.update(scrub)
        return cfg

    # Always override presaved config if defined in cli switch
    elif 'config_file' in cfg_cli_opts:
        _cfg_copy = merge_dicts(cfg,
                                yaml.load(
                                    slurp(cfg_cli_opts['config_file'])))
        scrub = sanitize_config_items(cfg_cli_opts)
        _cfg_copy.update(scrub)
        return _cfg_copy
    else:
        return sanitize_config_items(cfg_cli_opts)


def load_charms():
    """ Load known charm modules
    """
    import cloudinstall.charms

    charm_modules = [import_module('cloudinstall.charms.' + mname)
                     for (_, mname, _) in
                     pkgutil.iter_modules(cloudinstall.charms.__path__)]

    release_path = os.path.join(install_home(),
                                '.cloud-install/openstack_release')
    if os.path.exists(release_path):
        openstack_release = slurp(release_path)
    else:
        openstack_release = cloudinstall.charms.CharmBase.openstack_release_min

    charm_modules = [m for m in charm_modules if
                     (m.__charm_class__.openstack_release_min <=
                      openstack_release[0].lower())]
    return charm_modules


def load_charm_byname(name):
    """ Load a charm by name

    :param str name: name of charm
    """
    return import_module('cloudinstall.charms.{}'.format(name))


def merge_dicts(*dicts):
    """
    Return a new dictionary that is the result of merging the arguments
    together.
    In case of conflicts, later arguments take precedence over earlier
    arguments.

    Shamelessly copied from: http://stackoverflow.com/a/8795331/3170835
    """
    updated = {}
    # grab all keys
    keys = set()
    for d in dicts:
        keys = keys.union(set(d))

    for key in keys:
        values = [d[key] for d in dicts if key in d]
        # which ones are mapping types? (aka dict)
        maps = [value for value in values if isinstance(value, Mapping)]
        if maps:
            # if we have any mapping types, call recursively to merge them
            updated[key] = merge_dicts(*maps)
        else:
            # otherwise, just grab the last value we have, since later
            # arguments take precedence over earlier arguments
            updated[key] = values[-1]
    return updated


def render_charm_config(config):
    """ Render a config for setting charm config options

    If a custom charm config is passed on the cli it will
    attempt to merge those additional settings without losing
    any pre-existing charm options.
    """
    charm_conf = load_template('charmconf.yaml')
    template_args = dict(
        openstack_password=config.getopt('openstack_password'))

    if config.getopt('openstack_release'):
        template_args['openstack_release'] = config.getopt(
            'openstack_release')
        ubuntu_distname = platform.dist()[-1]
        openstack_origin = "cloud:{}-{}".format(
            ubuntu_distname, config.getopt('openstack_release'))
        template_args['openstack_origin'] = openstack_origin

    if config.is_single():
        template_args['worker_multiplier'] = '1'

    charm_conf_modified = charm_conf.render(**template_args)
    dest_yaml_path = os.path.join(config.cfg_path, 'charmconf.yaml')
    spew(dest_yaml_path, charm_conf_modified)

    # Check for custom charm options
    charm_conf_custom_file = config.getopt('charm_config_file')
    if charm_conf_custom_file and os.path.exists(charm_conf_custom_file):
        log.debug("Found custom charm config, updating charm settings.")
        charm_conf = yaml.load(slurp(dest_yaml_path))
        charm_conf_custom = yaml.load(
            slurp(config.getopt('charm_config_file')))
        charm_conf_merged = merge_dicts(charm_conf,
                                        charm_conf_custom)
        spew(dest_yaml_path, yaml.safe_dump(
            charm_conf_merged, default_flow_style=False))


def chown(path, user, group=None, recursive=False):
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
                shutil.chown(root, user, group)
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


def ensure_locale():
    """
    Makes sure LC_ALL is defined to something sensible
    """
    locale_conf = slurp('/etc/default/locale')
    for line in locale_conf.split('\n'):
        if line.startswith('#'):
            continue
        if "LC_ALL" in line:
            return
    new_locale = "LC_ALL=\"{}\"".format(os.getenv('LANG', 'C'))
    with open('/etc/default/locale', 'a+') as f:
        f.write(new_locale)
    return


def apt_install(pkgs):
    """ runs apt-get install against space separated list of `pkgs`
    """
    ensure_locale()
    cmd = ("DEBIAN_FRONTEND=noninteractive /usr/bin/apt-get -qyf "
           "-o Dpkg::Options::=--force-confdef "
           "-o Dpkg::Options::=--force-confold "
           "install {0}".format(pkgs))
    try:
        ret = check_call(cmd, stdout=DEVNULL, stderr=DEVNULL, shell=True)
        log.debug(ret)
    except CalledProcessError as e:
        log.error("Problem with package install: {0}".format(e))
        pass


def get_command_output(command, timeout=None, user_sudo=False):
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


def remote_cp(machine_id, src, dst, juju_home):
    log.debug("Remote copying {src} to {dst} on machine {m}".format(
        src=src,
        dst=dst,
        m=machine_id))
    ret = get_command_output(
        "{juju_home} juju scp {src} {m}:{dst}".format(
            juju_home=juju_home, src=src, dst=dst, m=machine_id))
    log.debug("Remote copy result: {r}".format(r=ret))


def remote_run(machine_id, cmds, juju_home):
    if type(cmds) is list:
        cmds = " && ".join(cmds)
    log.debug("Remote running ({cmds}) on machine {m}".format(
        m=machine_id, cmds=cmds))
    ret = get_command_output(
        "{juju_home} juju run "
        "--machine {m} '{cmds}'".format(juju_home=juju_home,
                                        m=machine_id,
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


class NoContainerIPException(Exception):

    "Container has no IP"


def container_ip(name):
    try:
        ips = check_output("sudo lxc-info -n {} -i -H".format(name),
                           shell=True)
        ips = ips.split()
        log.debug("lxc-info found: '{}'".format(ips))
        if len(ips) == 0:
            raise NoContainerIPException()
        log.debug("using {} as the container ip".format(ips[0].decode()))
        return ips[0].decode()
    except CalledProcessError:
        log.exception("error calling lxc-info to get container IP")
        raise NoContainerIPException()


class ContainerRunException(Exception):

    "Running cmd in container failed"


def container_run(name, cmd, use_ssh=False):
    """ run command in container

    :param str name: name of container
    :param str cmd: command to run
    """

    if use_ssh:
        ip = container_ip(name)
        quoted_cmd = shlex.quote(cmd)
        wrapped_cmd = ("sudo -H -u {3} TERM=xterm256-color ssh -t -q "
                       "-l ubuntu -o \"StrictHostKeyChecking=no\" "
                       "-o \"UserKnownHostsFile=/dev/null\" "
                       "-i {2} "
                       "{0} {1}".format(ip, quoted_cmd, ssh_privkey(),
                                        install_user()))
    else:
        ip = "-"
        quoted_cmd = cmd
        wrapped_cmd = ("lxc-attach -n {container_name} -- "
                       "{cmd}".format(container_name=name,
                                      cmd=cmd))

    log.debug("Running in container: {0}".format(wrapped_cmd))

    subproc = subprocess.Popen(wrapped_cmd, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    outs, errs = subproc.communicate()

    if subproc.returncode == 0:
        return outs.strip().decode('utf-8')
    else:
        log.debug("Error running command {} in container {}:{}\n"
                  "Output: '{}'\n"
                  "Stderr: '{}'".format(quoted_cmd, name, ip, outs, errs))

        raise ContainerRunException("Problem running {0} in container "
                                    "{1}:{2}".format(quoted_cmd, name, ip),
                                    subproc.returncode)


def container_run_status(name, cmd, config):
    """ Runs cloud-status in container
    """
    ip = container_ip(name)
    cmd = ("sudo -H -u {2} TERM=xterm256-color ssh -t -q "
           "-l ubuntu -o \"StrictHostKeyChecking=no\" "
           "-o \"UserKnownHostsFile=/dev/null\" "
           "-i {1} "
           "{0} {3}".format(ip, ssh_privkey(), install_user(), cmd))
    log.debug("Running command without waiting for response.: {}".format(cmd))
    args = deque(shlex.split(cmd))
    os.execlp(args.popleft(), *args)


def container_cp(name, filepath, dst):
    """ copy file to container

    :param str name: name of container
    :param str filepath: file to copy to container
    :param str dst: destination of remote path
    """
    ip = container_ip(name)
    cmd = ("scp -r -q "
           "-o \"StrictHostKeyChecking=no\" "
           "-o \"UserKnownHostsFile=/dev/null\" "
           "-i {identity} "
           "{filepath} "
           "ubuntu@{ip}:{dst} ".format(ip=ip, dst=dst,
                                       identity=ssh_privkey(),
                                       filepath=filepath))
    ret = get_command_output(cmd)
    if ret['status'] > 0:
        raise Exception("There was a problem copying ({0}) to the container "
                        "({1}:{2}): {3}".format(
                            filepath, name, ip, ret['output']))


def container_create(name, userdata):
    """ creates a container from ubuntu-cloud template
    """
    # NOTE: the -F template arg is a workaround. it flushes the lxc
    # ubuntu template's image cache and forces a re-download. It
    # should be removed after https://github.com/lxc/lxc/issues/381 is
    # resolved.
    flushflag = "-F"
    if os.getenv("USE_LXC_IMAGE_CACHE"):
        log.debug("USE_LXC_IMAGE_CACHE set, so not flushing in lxc-create")
        flushflag = ""
    out = get_command_output(
        'sudo lxc-create -t ubuntu-cloud '
        '-n {name} -- {flushflag} '
        '-u {userdatafilename}'.format(name=name,
                                       flushflag=flushflag,
                                       userdatafilename=userdata))
    if out['status'] > 0:
        raise Exception("Unable to create container: "
                        "{0}".format(out['output']))
    return out['status']


def container_start(name, lxc_logfile):
    """ starts lxc container

    :param str name: name of container
    """
    out = get_command_output(
        'sudo lxc-start -n {0} -d -o {1}'.format(name,
                                                 lxc_logfile))

    if out['status'] > 0:
        raise Exception("Unable to start container: "
                        "{0}".format(out['output']))
    return out['status']


def container_stop(name):
    """ stops lxc container

    :param str name: name of container
    """
    out = get_command_output(
        'sudo lxc-stop -n {0}'.format(name))

    if out['status'] > 0:
        raise Exception("Unable to stop container: "
                        "{0}".format(out['output']))

    return out['status']


def container_destroy(name):
    """ destroys lxc container

    :param str name: name of container
    """
    out = get_command_output(
        'sudo lxc-destroy -n {0}'.format(name))

    if out['status'] > 0:
        raise Exception("Unable to destroy container: "
                        "{0}".format(out['output']))

    return out['status']


def container_wait_checked(name, check_logfile, interval=20):
    """waits for container to be in RUNNING state, checking
    'check_logfile' every 'interval' seconds for error messages.

    Intended to be used with container_start, which uses 'lxc-start
    -d', which returns 0 immediately and does not detect errors.

    returns when the container 'name' is in RUNNING state.
    raises an exception if errors are detected.
    """
    while True:
        out = get_command_output('sudo lxc-wait -n {} -s RUNNING '
                                 '-t {}'.format(name, interval))
        if out['status'] == 0:
            return
        log.debug("{} not RUNNING after {} seconds, "
                  "checking '{}' for errors".format(name, interval,
                                                    check_logfile))
        grepout = get_command_output('grep -q ERROR {}'.format(check_logfile))
        if grepout['status'] == 0:
            raise Exception("Error detected starting container. See {} "
                            "for details.".format(check_logfile))


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
    return os.path.expanduser("~" + install_user())


def ssh_readkey():
    """ reads ssh key
    """
    with open(ssh_pubkey(), 'r') as f:
        return f.read()


def ssh_genkey():
    """ Generates sshkey
    """
    if not os.path.exists(ssh_privkey()):
        user_sshkey_path = os.path.join(install_home(),
                                        '.ssh/id_rsa')
        cmd = "ssh-keygen -N '' -f {0}".format(user_sshkey_path)
        out = get_command_output(cmd, user_sudo=True)
        if out['status'] != 0:
            raise Exception(
                "Unable to generate key: {0}".format(out['output']))
        get_command_output('sudo chown -R {0} {1}'.format(
            install_user(),
            os.path.join(install_home(), '.ssh')))
        get_command_output('chmod 0644 {0}.pub'.format(user_sshkey_path),
                           user_sudo=True)
    else:
        log.debug('ssh keys exist for this user, they will be used instead.')


def read_ini(path):
    """ Reads a basic INI like file without sections headers.
    Prepends a default section header for querying.
    """
    ini = open(path)
    config = configparser.ConfigParser()
    config.read_file(itertools.chain(['[DEFAULT]'], ini))
    return config


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
        try:
            chown(path, owner)
        except:
            raise UtilsException("Unable to set ownership of {}".format(path))


def slurp(path):
    """ Reads data from path

    :param str path: path of file
    """
    try:
        with open(path) as f:
            return f.read().strip()
    except IOError:
        raise IOError


def human_to_mb(s):
    """Translates human-readable strings like '10G' to numeric
    megabytes"""

    if len(s) == 0:
        raise Exception("unexpected empty string")

    md = dict(M=1, G=1024, T=1024 * 1024, P=1024 * 1024 * 1024)
    suffix = s[-1]
    if suffix.isalpha():
        return float(s[:-1]) * md[suffix]
    else:
        return float(s)


def mb_to_human(num):
    """Translates float number of bytes into human readable strings."""
    suffixes = ['M', 'G', 'T', 'P']
    if num == 0:
        return '0 B'

    i = 0
    while num >= 1024 and i < len(suffixes) - 1:
        num /= 1024
        i += 1
    return "{:.2f} {}".format(num, suffixes[i])


def format_constraint(k, v):
    vs = str(v)
    if vs.isdecimal():
        vs = mb_to_human(v)
    return "{}={}".format(k, vs)


def make_screen_hicolor(screen):
    """returns a screen to pass to MainLoop init
    with 256 colors.
    """
    screen.set_terminal_properties(256)
    screen.reset_default_terminal_palette()
    return screen


def get_hicolor_screen(palette):
    screen = urwid.raw_display.Screen()
    screen.register_palette(palette)
    return make_screen_hicolor(screen)


def macgen():
    """ generates mac addresses
    """
    mac = [0x00, 0x16, 0x3e,
           random.randint(0x00, 0x7f),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))
