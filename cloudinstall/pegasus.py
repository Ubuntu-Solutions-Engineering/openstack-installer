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

from io import StringIO
from collections import defaultdict
import os
from os.path import expanduser, exists
from subprocess import check_call, DEVNULL
from textwrap import dedent
import tempfile
import re
import urllib

from cloudinstall import utils
from cloudinstall.maas import MaasState
from cloudinstall.maas.auth import MaasAuth
from cloudinstall.juju import JujuState
from cloudinstall.maas.client import MaasClient


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


class MaasLoginFailure(Exception):
    MESSAGE = "Could not read login credentials. Please run: " \
              "maas-get-user-creds root > ~/.cloud-install/maas-creds"


def get_charm_relations(charm):
    """ Return a list of (relation, command) of relations to add. """
    for rel in RELATIONS.get(charm, []):
        if charm == NOVA_COMPUTE and rel == RABBITMQ_SERVER:
            c, r = (NOVA_COMPUTE + ":amqp", RABBITMQ_SERVER + ":amqp")
        else:
            c, r = (charm, rel)
        cmd = "juju add-relation {charm} {relation}"
        yield (r, cmd.format(charm=c, relation=r))

PASSWORD_FILE = expanduser('~/.cloud-install/openstack.passwd')
try:
    with open(PASSWORD_FILE) as f:
        OPENSTACK_PASSWORD = f.read().strip()
except IOError:
    OPENSTACK_PASSWORD = None

# This is kind of a hack. juju deploy $foo rejects foo if it doesn't have a
# config or there aren't any options in the declared config. So, we have to
# babysit it and not tell it about configs when there aren't any.
_OMIT_CONFIG = [
    MYSQL,
    RABBITMQ_SERVER,
]

# TODO: Use trusty + icehouse
CONFIG_TEMPLATE = dedent("""\
    glance:
        openstack-origin: cloud:precise-grizzly
    keystone:
        openstack-origin: cloud:precise-grizzly
        admin-password: {password}
    nova-cloud-controller:
        openstack-origin: cloud:precise-grizzly
    nova-compute:
        openstack-origin: cloud:precise-grizzly
    openstack-dashboard:
        openstack-origin: cloud:precise-grizzly
""").format(password=OPENSTACK_PASSWORD)

SINGLE_SYSTEM = exists(expanduser('~/.cloud-install/single'))
MULTI_SYSTEM = exists(expanduser('~/.cloud-install/multi'))

def juju_config_arg(charm):
    """ Query configuration parameters for openstack charms

    :param charm: name of charm
    :type charm: str
    :return: path of openstack configuration
    :rtype: str
    """
    path = os.path.join(tempfile.gettempdir(), "openstack.yaml")
    if not exists(path):
        with open(path, 'wb') as f:
            f.write(bytes(CONFIG_TEMPLATE, 'utf-8'))
    config = "" if charm in _OMIT_CONFIG else "--config {path}"
    return config.format(path=path)


def poll_state():
    """ Polls current state of Juju and MAAS
    """
    # Capture Juju state
    juju = utils._run('juju status')
    if not juju:
        raise Exception("Juju State is empty!")
    juju = JujuState(StringIO(juju.decode('ascii')))

    maas = None
    if MULTI_SYSTEM:
        # Login to MAAS
        auth = MaasAuth()
        auth.get_api_key('root')
        auth.login()

        # Load Client routines
        c = MaasClient(auth)

        # Capture Maas state
        maas = MaasState(c.nodes)
        c.tag_fpi(maas)
        c.nodes_accept_all()
        c.tag_name(maas)
    return parse_state(juju, maas), juju


def parse_state(juju, maas=None):
    """ Parses the current state of juju containers and maas nodes

    :param juju: juju polled state
    :type juju: .. class:: JujuState()
    :param maas: maas polled state
    :type mass: .. class:: MaasState()
    :return: nodes/containers
    :rtype: list
    """
    results = []

    if maas:
        for machine in maas:
            m = juju.machine(machine['resource_uri']) or \
                {"machine_no": -1, "agent-state": "unallocated"}

            if machine['hostname'].startswith('juju-bootstrap'):
                continue

            d = {
                "fqdn": machine['hostname'],
                "memory": machine['memory'],
                "cpu_count": machine['cpu_count'],
                "storage": str(int(machine['storage']) / 1024),  # MB => GB
                "tag": machine['system_id'],
                "machine_no": m["machine_no"],
                "agent_state": m["agent-state"],
            }
            charms, units = juju.assignments.get(machine['resource_uri'], ([], []))
            if charms:
                d['charms'] = charms
            if units:
                d['units'] = units

            # We only want to list nodes that are already assigned to our juju
            # instance or that could be assigned to our juju instance; nodes
            # allocated to other users should be ignored, however, we have no way
            # to distinguish those in the API currently, so we just add everything.
            results.append(d)

    if MULTI_SYSTEM:
        for machine in juju.machines:
            for container in machine.containers:
                d = {
                    "fqdn": container.dns_name,
                    "memory": "LXC",
                    "cpu_count": "LXC",
                    "storage": "LXC",
                    "machine_no": container.machine_id,
                    "agent_state": "LXC",
                    "charms": container.charms,
                    "units": container.units,
                }
                results.append(d)
    if SINGLE_SYSTEM:
        for machine in juju.machines:

            if '0' in machine.machine_id:
                continue

            d = {
                "fqdn": machine.dns_name,
                "memory": machine.mem,
                "cpu_count": machine.cpu_cores,
                "storage": machine.storage,
                "machine_no": machine.machine_id,
                "agent_state": machine.agent_state,
                "charms": machine.charms,
                "units": machine.units
            }
            results.append(d)
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
