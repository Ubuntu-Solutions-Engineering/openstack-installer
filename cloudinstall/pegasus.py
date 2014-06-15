#
# pegasus.py - GUI interface to Cloud Installer
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

import logging
from os.path import expanduser, exists
from subprocess import check_call

from cloudinstall import utils
from cloudinstall.maas import MaasState
from cloudinstall.maas.auth import MaasAuth
from cloudinstall.juju import JujuState
from cloudinstall.maas.client import MaasClient

log = logging.getLogger('cloudinstall.pegasus')

NOVA_CLOUD_CONTROLLER = "nova-cloud-controller"
MYSQL = 'mysql'
RABBITMQ_SERVER = 'rabbitmq-server'
GLANCE = 'glance'
KEYSTONE = 'keystone'
OPENSTACK_DASHBOARD = 'openstack-dashboard'
NOVA_COMPUTE = 'nova-compute'
SWIFT = 'swift-storage'
CEPH = 'ceph'

CONTROLLER = "Controller"
COMPUTE = "Compute"
OBJECT_STORAGE = "Object Storage"
BLOCK_STORAGE = "Block Storage"

# NOTE: this appears to be out of date
# see LP bug 1319222
ALLOCATION = {
    NOVA_CLOUD_CONTROLLER: CONTROLLER,
    NOVA_COMPUTE: COMPUTE,
    SWIFT: OBJECT_STORAGE,
    CEPH: BLOCK_STORAGE,
}

CONTROLLER_CHARMS = [
    NOVA_CLOUD_CONTROLLER,
    MYSQL,
    RABBITMQ_SERVER,
    GLANCE,
    KEYSTONE,
    OPENSTACK_DASHBOARD,
]

PASSWORD_FILE = expanduser('~/.cloud-install/openstack.passwd')
try:
    with open(PASSWORD_FILE) as f:
        OPENSTACK_PASSWORD = f.read().strip()
except IOError:
    OPENSTACK_PASSWORD = 'password'


# Determine installation type
SINGLE_SYSTEM = exists(expanduser('~/.cloud-install/single'))
MULTI_SYSTEM = exists(expanduser('~/.cloud-install/multi'))


def poll_state():
    """ Polls current state of Juju and MAAS

    :returns: list of Machine() and the Juju state
    :rtype: tuple (JujuState(), MaasState())
    """
    # Capture Juju state
    cmd = utils.get_command_output('juju status',
                                   combine_output=False)
    if cmd['ret']:
        raise SystemExit("Error connecting to juju: stderr: {e}".format(
            e=cmd['stderr']))
    juju = JujuState(cmd['stdout'])

    maas = None
    if MULTI_SYSTEM:
        # Login to MAAS
        auth = MaasAuth()
        auth.get_api_key('root')
        # auth.login()

        # Load Client routines
        c = MaasClient(auth)

        # Capture Maas state
        maas = MaasState(c.nodes)
        c.tag_fpi(maas)
        c.nodes_accept_all()
        c.tag_name(maas)

    update_machine_info(juju, maas)
    return (juju, maas)


def update_machine_info(juju, maas=None):
    """Parses the current state of juju containers and maas nodes.

    Updates machine info in-place.

    :param juju: juju polled state
    :type juju: JujuState()
    :param maas: maas polled state
    :type mass: MaasState()

    """

    for machine in juju.machines():

        if machine.machine_id == "0":
            continue

        if SINGLE_SYSTEM:
            for c in machine.containers:
                c.mem = utils.get_host_mem()
                c.cpu_cores = utils.get_host_cpu_cores()
                c.storage = utils.get_host_storage()

    if maas:
        for machine in maas.machines():
            if machine.status == 4:
                machine.agent_state = "ready"
            if machine.status == 6:
                machine.agent_state = "allocated"
            machine.dns_name = machine.hostname
            log.debug("querying maas machine: {maas}".format(maas=machine))


def wait_for_services():
    """ Wait for services to be in ready state

    .. todo::

    Is this still needed?
    """
    services = [
        'maas-region-celery',
        'maas-cluster-celery',
        'maas-pserv',
        'maas-txlongpoll',
        'juju-db',
        'jujud-machine-0',
    ]

    for service in services:
        check_call(['start', 'wait-for-state', 'WAITER=cloud-install-status',
                    'WAIT_FOR=%s' % service, 'WAIT_STATE=running'])
