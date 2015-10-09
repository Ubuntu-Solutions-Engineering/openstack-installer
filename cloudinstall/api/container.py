#
# Copyright 2014, 2015 Canonical, Ltd.
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

import subprocess
from subprocess import (check_output,
                        CalledProcessError)
import logging
import shlex
import pty
import os
import codecs
import errno
from collections import deque
from cloudinstall import utils

log = logging.getLogger("cloudinstall.api.container")


class NoContainerIPException(Exception):

    "Container has no IP"


class ContainerRunException(Exception):

    "Running cmd in container failed"


class Container:
    @classmethod
    def ip(cls, name):
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

    @classmethod
    def run(cls, name, cmd, use_ssh=False, use_sudo=False, output_cb=None):
        """ run command in container

        :param str name: name of container
        :param str cmd: command to run
        """

        if use_ssh:
            ip = cls.ip(name)
            quoted_cmd = shlex.quote(cmd)
            wrapped_cmd = ("sudo -H -u {3} TERM=xterm256-color ssh -t -q "
                           "-l ubuntu -o \"StrictHostKeyChecking=no\" "
                           "-o \"UserKnownHostsFile=/dev/null\" "
                           "-o \"ControlMaster=auto\" "
                           "-o \"ControlPersist=600\" "
                           "-i {2} "
                           "{0} {1}".format(ip, quoted_cmd,
                                            utils.ssh_privkey(),
                                            utils.install_user()))
        else:
            ip = "-"
            quoted_cmd = cmd
            wrapped_cmd = []
            if use_sudo:
                wrapped_cmd.append("sudo")
            wrapped_cmd.append("lxc-attach -n {container_name} -- "
                               "{cmd}".format(container_name=name,
                                              cmd=cmd))
            wrapped_cmd = " ".join(wrapped_cmd)

        stdoutmaster, stdoutslave = pty.openpty()
        subproc = subprocess.Popen(wrapped_cmd, shell=True,
                                   stdout=stdoutslave,
                                   stderr=subprocess.PIPE)
        os.close(stdoutslave)
        decoder = codecs.getincrementaldecoder('utf-8')()

        def last_ten_lines(s):
            chunk = s[-1500:]
            lines = chunk.splitlines(True)
            return ''.join(lines[-10:]).replace('\r', '')

        decoded_output = ""
        try:
            while subproc.poll() is None:
                try:
                    b = os.read(stdoutmaster, 512)
                except OSError as e:
                    if e.errno != errno.EIO:
                        raise
                    break
                else:
                    final = False
                    if not b:
                        final = True
                    decoded_chars = decoder.decode(b, final)
                    if decoded_chars is None:
                        continue

                    decoded_output += decoded_chars
                    if output_cb:
                        ls = last_ten_lines(decoded_output)

                        output_cb(ls)
                    if final:
                        break
        finally:
            os.close(stdoutmaster)
            if subproc.poll() is None:
                subproc.kill()
            subproc.wait()

        errors = [l.decode('utf-8') for l in subproc.stderr.readlines()]
        if output_cb:
            output_cb(last_ten_lines(decoded_output))

        errors = ''.join(errors)

        if subproc.returncode == 0:
            return decoded_output.strip()
        else:
            raise ContainerRunException("Problem running {0} in container "
                                        "{1}:{2}".format(quoted_cmd, name, ip),
                                        subproc.returncode)

    @classmethod
    def run_status(cls, name, cmd, config):
        """ Runs cloud-status in container
        """
        ip = cls.ip(name)
        cmd = ("sudo -H -u {2} TERM=xterm256-color ssh -t -q "
               "-l ubuntu -o \"StrictHostKeyChecking=no\" "
               "-o \"UserKnownHostsFile=/dev/null\" "
               "-o \"ControlMaster=auto\" "
               "-o \"ControlPersist=600\" "
               "-i {1} "
               "{0} {3}".format(ip, utils.ssh_privkey(),
                                utils.install_user(), cmd))
        log.debug("Running command without waiting "
                  "for response.: {}".format(cmd))
        args = deque(shlex.split(cmd))
        os.execlp(args.popleft(), *args)

    @classmethod
    def cp(cls, name, filepath, dst):
        """ copy file to container

        :param str name: name of container
        :param str filepath: file to copy to container
        :param str dst: destination of remote path
        """
        ip = cls.ip(name)
        cmd = ("scp -r -q "
               "-o \"StrictHostKeyChecking=no\" "
               "-o \"UserKnownHostsFile=/dev/null\" "
               "-i {identity} "
               "{filepath} "
               "ubuntu@{ip}:{dst} ".format(ip=ip, dst=dst,
                                           identity=utils.ssh_privkey(),
                                           filepath=filepath))
        ret = utils.get_command_output(cmd)
        if ret['status'] > 0:
            raise Exception("There was a problem copying ({0}) to the "
                            "container ({1}:{2}): {3}".format(
                                filepath, name, ip, ret['output']))

    @classmethod
    def create(cls, name, userdata):
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
        out = utils.get_command_output(
            'sudo -E lxc-create -t ubuntu-cloud '
            '-n {name} -- {flushflag} '
            '-u {userdatafilename}'.format(name=name,
                                           flushflag=flushflag,
                                           userdatafilename=userdata))
        if out['status'] > 0:
            raise Exception("Unable to create container: "
                            "{0}".format(out['output']))
        return out['status']

    @classmethod
    def start(cls, name, lxc_logfile):
        """ starts lxc container

        :param str name: name of container
        """
        out = utils.get_command_output(
            'sudo lxc-start -n {0} -d -o {1}'.format(name,
                                                     lxc_logfile))

        if out['status'] > 0:
            raise Exception("Unable to start container: "
                            "{0}".format(out['output']))
        return out['status']

    @classmethod
    def stop(cls, name):
        """ stops lxc container

        :param str name: name of container
        """
        out = utils.get_command_output(
            'sudo lxc-stop -n {0}'.format(name))

        if out['status'] > 0:
            raise Exception("Unable to stop container: "
                            "{0}".format(out['output']))

        return out['status']

    @classmethod
    def destroy(cls, name):
        """ destroys lxc container

        :param str name: name of container
        """
        out = utils.get_command_output(
            'sudo lxc-destroy -n {0}'.format(name))

        if out['status'] > 0:
            raise Exception("Unable to destroy container: "
                            "{0}".format(out['output']))

        return out['status']

    @classmethod
    def wait_checked(cls, name, check_logfile, interval=20):
        """waits for container to be in RUNNING state, checking
        'check_logfile' every 'interval' seconds for error messages.

        Intended to be used with container_start, which uses 'lxc-start
        -d', which returns 0 immediately and does not detect errors.

        returns when the container 'name' is in RUNNING state.
        raises an exception if errors are detected.
        """
        while True:
            out = utils.get_command_output('sudo lxc-wait -n {} -s RUNNING '
                                           '-t {}'.format(name, interval))
            if out['status'] == 0:
                return
            log.debug("{} not RUNNING after {} seconds, "
                      "checking '{}' for errors".format(name, interval,
                                                        check_logfile))
            grepout = utils.get_command_output(
                'grep -q ERROR {}'.format(check_logfile))
            if grepout['status'] == 0:
                raise Exception("Error detected starting container. See {} "
                                "for details.".format(check_logfile))

    @classmethod
    def wait(cls, name):
        """ waits for the container to be in a RUNNING state

        :param str name: name of container
        """
        out = utils.get_command_output(
            'sudo lxc-wait -n {0} -s RUNNING'.format(name))
        return out['status']
