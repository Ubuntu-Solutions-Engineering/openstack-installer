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
from io import StringIO
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

RELATIONS = {
    KEYSTONE: [MYSQL],
    NOVA_CLOUD_CONTROLLER: [MYSQL, RABBITMQ_SERVER, GLANCE, KEYSTONE],
    NOVA_COMPUTE: [MYSQL, RABBITMQ_SERVER, GLANCE, NOVA_CLOUD_CONTROLLER],
    GLANCE: [MYSQL, KEYSTONE],
    OPENSTACK_DASHBOARD: [KEYSTONE],
}

###############################################################################
# TODO: Remove since charm relations are handled per charm class
# Handle charm relations
# def get_charm_relations(charm):
#     """ Return a list of (relation, command) of relations to add. """
#     for rel in RELATIONS.get(charm, []):
#         if charm == NOVA_COMPUTE and rel == RABBITMQ_SERVER:
#             c, r = (NOVA_COMPUTE + ":amqp", RABBITMQ_SERVER + ":amqp")
#         else:
#             c, r = (charm, rel)
#         cmd = "juju add-relation {charm} {relation}"
#         yield (r, cmd.format(charm=c, relation=r))
###############################################################################

PASSWORD_FILE = expanduser('~/.cloud-install/openstack.passwd')
try:
    with open(PASSWORD_FILE) as f:
        OPENSTACK_PASSWORD = f.read().strip()
except IOError:
    OPENSTACK_PASSWORD = 'password'


# Determine installation type
SINGLE_SYSTEM = exists(expanduser('~/.cloud-install/single'))
MULTI_SYSTEM = exists(expanduser('~/.cloud-install/multi'))

###############################################################################
# FIXME: With addition of Openstack charms to Trusty
# we shouldn't need to use a configuration file for specifying
# the openstack-origin as it will default to 'distro' which
# in this case is Trusty's openstack charms.
#
# def juju_config_arg(charm):
#     """ Query configuration parameters for openstack charms
#
#     :param charm: name of charm
#     :type charm: str
#     :return: path of openstack configuration
#     :rtype: str
#     """
#     path = os.path.join(tempfile.gettempdir(), "openstack.yaml")
#     with open(path, 'wb') as f:
#         f.write(bytes(CONFIG_TEMPLATE, 'utf-8'))
#     config = "" if charm in _OMIT_CONFIG else "--config {path}"
#     return config.format(path=path)
###############################################################################

def poll_state():
    """ Polls current state of Juju and MAAS

    :returns: list of Machine() and the Juju state
    :rtype: list, JujuState()
    """
    # Capture Juju state
    ret, juju, _ = utils.get_command_output('juju status')
    if ret:
        log.debug("Juju state unknown, will re-poll in " \
                  "case bootstrap is taking a little longer to come up.")
        # Stub out a juju status for now
        juju = JujuState('environment: local\nmachines:')
    else:
        juju = JujuState(StringIO(juju))

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
    return parse_state(juju, maas), juju


def parse_state(juju, maas=None):
    """Parses the current state of juju containers and maas nodes.

    Returns a list of machines excluding the bootstrap node, juju
    machine ID "0".

    :param juju: juju polled state
    :type juju: JujuState()
    :param maas: maas polled state
    :type mass: MaasState()
    :return: nodes/containers
    :rtype: list

    """
    results = []

    for machine in juju.machines():

        if machine.machine_id == "0":
            continue

        if SINGLE_SYSTEM:
            for c in machine.containers:
                c.mem = utils.get_host_mem()
                c.cpu_cores = utils.get_host_cpu_cores()
                c.storage = utils.get_host_storage()

        if maas:
            maas_machine = maas.machine(machine.instance_id)
            if maas_machine is None:
                log.debug("machine id='{iid}' not found in MaasState.".format(iid=machine.instance_id))
            else:
                machine.mem = maas_machine.mem
                machine.cpu_cores = maas_machine.cpu_cores
                machine.storage = maas_machine.storage
                machine.tag = maas_machine.tag
        results.append(machine)
    return results


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
