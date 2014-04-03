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
import yaml
import json
from textwrap import dedent
import tempfile
import re
import urllib

from cloudinstall import utils
from cloudinstall.maas.state import MaasState
from cloudinstall.juju.state import JujuState
from cloudinstall.maas.client import MaasClient


NOVA_CLOUD_CONTROLLER = "nova-cloud-controller"
MYSQL = 'mysql'
RABBITMQ_SERVER = 'rabbitmq-server'
GLANCE = 'glance'
KEYSTONE = 'keystone'
OPENSTACK_DASHBOARD = 'openstack-dashboard'
NOVA_COMPUTE = 'nova-compute'
SWIFT = 'swift'
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

# TODO: Use trusty + havana
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
    path = os.path.join(tempfile.gettempdir(), "openstack.yaml")
    if not exists(path):
        with open(path, 'wb') as f:
            f.write(bytes(CONFIG_TEMPLATE, 'utf-8'))
    config = "" if charm in _OMIT_CONFIG else "--config {path}"
    return config.format(path=path)


def poll_state(auth=None):
    """ Polls current state of Juju and MAAS

    @param auth: MAAS Auth class
    """
    # Capture Juju state
    juju = utils._run('juju status')
    if not juju:
        raise Exception("Juju State is empty!")
    juju = JujuState(StringIO(juju.decode('ascii')))

    # Login to MAAS
    maas = None
    if auth and not auth.is_logged_in:
        auth.get_api_key('root')
        auth.login()

        # Load Client routines
        m_client = MaasClient(auth=auth)

        # Capture Maas state
        maas = MaasState(m_client.nodes)
        m_client.tag_fpi(maas)
        m_client.nodes_accept_all()
        m_client.tag_name(maas)
    return parse_state(juju, maas), juju


def parse_state(juju, maas=None):
    """ Parses the current state of juju containers and maas nodes

    @param juju: juju polled state
    @param maas: maas polled state
    @return: list of nodes/containers created
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

    for container, (charms, units) in juju.containers.items():
        machine_no, _, lxc_id = container.split('/')
        d = {
            "fqdn": juju.container(machine_no, lxc_id)['dns-name'],
            "memory": "LXC",
            "cpu_count": "LXC",
            "storage": "LXC",
            "machine_no": container,
            "agent_state": "LXC",
            "charms": charms,
            "units": units,
        }
        results.append(d)
    return results


def wait_for_services():
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


class StartKVM:
    CONFIG_TEMPLATE = """#cloud-config
datasource:
  MAAS: {{consumer_key: {consumer_key}, metadata_url: 'http://localhost/MAAS/metadata',
    token_key: {token_key}, token_secret: {token_secret}}}
"""
    MAAS_CREDS = os.path.expanduser('~/.cloud-install/maas-creds')
    USER_DATA = os.path.join(tempfile.gettempdir(), 'uvt_user_data')
    SLAVE_PREFIX = 'slave'

    def next_host(self):
        def extract_id(self, host):
            m = re.match(self.SLAVE_PREFIX + '(\d*)', host)
            if m:
                return int(m.groups()[0])
            else:
                return -1
        out = subprocess.check_output(
            ['uvt-kvm', 'list']).decode('utf-8').split('\n')
        return max(map(self.extract_id, out)) + 1 if out else 0

    def find_path(self, hostname):
        vols = subprocess.check_output(
            ['virsh', 'vol-list', 'uvtool']).split('\n')
        for vol in vols:
            if vol.startswith(self.hostname + '.img'):
                return vol.split()[1]
        return None

    def run(self):
        if not os.path.exists(self.USER_DATA):
            with open(self.MAAS_CREDS) as f:
                [consumer_key,
                 token_key,
                 token_secret] = f.read().strip().split(':')
                with open(self.USER_DATA, 'wb') as f:
                    content = self.CONFIG_TEMPLATE.format(
                        consumer_key=consumer_key, token_key=token_key,
                        token_secret=token_secret)
                f.write(bytes(content, 'utf-8'))

        hostname = self.SLAVE_PREFIX + str(self.next_host())

        uvt = ['uvt-kvm', 'create', '--bridge', 'br0', hostname]
        subprocess.check_call(uvt)

        # Immediately power off the machine so we can make our edits
        # to its disk.  uvt-kvm will support some kind of --no-start
        # option in the future so we don't have to do this.
        subprocess.check_call(['virsh', 'destroy', hostname])

        # Put our cloud-init config in the disk image.
        subprocess.check_call('add_maas_data', find_path(hostname), USER_DATA)

        # Start the machine back up
        subprocess.check_call(['virsh', 'start', hostname])

        subprocess.check_call(['maas', 'maas', 'nodes',
                               'new', 'hostname=' + hostname])
        creds = os.path.join(tempfile.gettempdir(), 'maas.creds')
        with open(creds, 'wb') as f:
            req = urllib.urlopen(
                'http://localhost/MAAS/metadata/latest/by-id/%s/?op=get_preseed' % (hostname,))
            f.write(req.read())
        subprocess.check_call(['maas-signal', '--config', creds, 'OK'])
