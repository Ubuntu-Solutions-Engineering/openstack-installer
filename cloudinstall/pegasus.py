#
# pegasus.py - GUI interface to Cloud Installer
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This package is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# On Debian systems, the complete text of the GNU General
# Public License version 3 can be found in "/usr/share/common-licenses/GPL-3".

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

import utils

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

PASSWORD_FILE = expanduser('~/.cloud-install/openstack.passwd')
try:
    with open(PASSWORD_FILE) as f:
        OPENSTACK_PASSWORD = f.read().strip()
except IOError:
    OPENSTACK_PASSWORD=None

# This is kind of a hack. juju deploy $foo rejects foo if it doesn't have a
# config or there aren't any options in the declared config. So, we have to
# babysit it and not tell it about configs when there aren't any.
_OMIT_CONFIG = [
    MYSQL,
    RABBITMQ_SERVER,
]

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

def juju_config_arg(charm):
    path = os.path.join(tempfile.gettempdir(), "openstack.yaml")
    if not exists(path):
        with open(path, 'wb') as f:
            f.write(bytes(CONFIG_TEMPLATE, 'utf-8'))
    config = "" if charm in _OMIT_CONFIG else "--config {path}"
    return config.format(path=path)


class JujuState:
    def __init__(self, raw_yaml):
        """ Builds a JujuState from a file-like object containing the raw
        output from 'juju status'"""
        self._yaml = yaml.load(raw_yaml)

    def id_for_machine_no(self, no):
        return self._yaml['machines'][no]['instance-id']

    def machine(self, id):
        for no, m in self._yaml['machines'].items():
            if m['instance-id'] == id:
                m['machine_no'] = no
                return m

    @property
    def services(self):
        """ Map of {servicename: nodecount}. """
        ret = {}
        for svc, contents in self._yaml.get('services', {}).items():
            ret[svc] = len(contents.get('units', []))
        return ret

    def _build_unit_map(self, compute_id, allow_id):
        """ Return a map of compute_id(unit): ([charm name], [unit name]),
        useful for defining maps between properties of units and what is
        deployed to them. """
        charms = defaultdict(lambda: ([], []))
        for name, service in self._yaml.get('services', {}).items():
            for unit_name, unit in service.get('units', {}).items():
                if 'machine' not in unit or not allow_id(str(unit['machine'])):
                    continue
                cs, us = charms[compute_id(unit)]
                cs.append(name)
                us.append(unit_name)
        return charms

    @property
    def assignments(self):
        """ Return a map of instance-id: ([charm name], [unit name]), useful
        for figuring out what is deployed where. Note that these are physical
        machines, and containers are not included. """
        def by_instance_id(unit):
            return self._yaml['machines'][unit['machine']]['instance-id']
        def not_lxc(id_):
            return 'lxc' not in id_
        return self._build_unit_map(by_instance_id, not_lxc)

    @property
    def containers(self):
        """ A map of container-id (e.g. "1/lxc/0") to ([charm name], [unit
        name]) """
        def by_machine_name(unit):
            return unit['machine']
        def is_lxc(id_):
            return 'lxc' in id_
        return self._build_unit_map(by_machine_name, allow_id=is_lxc)

class MaasState:
    DECLARED = 0
    COMMISSIONING = 1
    FAILED_TESTS = 2
    MISSING = 3
    READY = 4
    RESERVED = 5
    ALLOCATED = 6
    RETIRED = 7
    def __init__(self, raw_json):
        self._json = json.load(raw_json)

    def __iter__(self):
        return iter(self._json)

    def hostname_for_instance_id(self, id):
        for machine in self:
            if machine['resource_uri'] == id:
                return machine['hostname']

    @property
    def machines(self):
        return len(self._json)

    def num_in_state(self, state):
        return len(list(filter(lambda m: int(m["status"]) == state, self._json)))

def parse_state(juju, maas):
    results = []

    for machine in maas:
        m = juju.machine(machine['resource_uri']) or \
            {"machine_no": -1, "agent-state": "unallocated"}
        d = {
            "fqdn": machine['hostname'],
            "memory": machine['memory'],
            "cpu_count": machine['cpu_count'],
            "storage": str(int(machine['storage']) / 1024), # MB => GB
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
        hostname = maas.hostname_for_instance_id(juju.id_for_machine_no(machine_no))
        d = {
            # TODO: this really needs to be network visible, maybe we should
            # use the IP instead?
            "fqdn": hostname,
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

class MaasLoginFailure(Exception):
    MESSAGE = "Could not read login credentials. Please run:" \
    "    maas-get-user-creds root > ~/.cloud-install/maas-creds"


def maas_login():
    try:
        with open(expanduser('~/.cloud-install/maas-creds')) as f:
            creds = f.read()
            utils._run('maas-cli login maas http://localhost/MAAS %s' % creds)
    except IOError as e:
        raise MaasLoginFailure(str(e))


def ensure_tag(tag):
    """ Create tag if it doesn't exist. """
    list_out = StringIO(utils._run('maas-cli maas tags list').decode('ascii'))
    tags = {tagmd['name'] for tagmd in json.load(list_out)}
    if tag not in tags:
        check_call(['maas-cli', 'maas', 'tags', 'new', 'name=%s' % tag],
                    stderr=DEVNULL, stdout=DEVNULL)


def tag_machine(tag, system_id):
    """ Tag the machine with the specified tag. """
    check_call(['maas-cli', 'maas', 'tag', 'update-nodes', tag,
                'add=%s' % system_id], stderr=DEVNULL, stdout=DEVNULL)


def name_tag(maas):
    """ Tag each node as its hostname. """
    # This is a bit ugly. Since we want to be able to juju deploy to a
    # particular node that the user has selected, we use juju's constraints
    # support for maas. Unfortunately, juju didn't implement maas-name
    # directly, we have to tag each node with its hostname for now so that we
    # can pass that tag as a constraint to juju.
    for machine in maas:
        tag = machine['system_id']
        if 'tag_names' not in machine or tag not in machine['tag_names']:
            ensure_tag(tag)
            tag_machine(tag, tag)


def fpi_tag(maas):
    """ Tag each DECLARED host with the FPI tag. """
    # Also a little strange: we could define a tag with 'definition=true()' and
    # automatically tag each node. However, each time we un-tag a node, maas
    # evaluates the xpath expression again and re-tags it. So, we do it
    # once, manually, when the machine is in the DECLARED state (also to
    # avoid re-tagging things that have already been tagged).
    FPI_TAG = 'use-fastpath-installer'
    ensure_tag(FPI_TAG)
    for machine in maas:
        if machine['status'] == MaasState.DECLARED:
            tag_machine(FPI_TAG, machine['system_id'])


def poll_state():
    juju = utils._run('juju status')
    if not juju:
        raise Exception("Juju State is empty!")
    juju = JujuState(StringIO(juju.decode('ascii')))
    maas_login()
    maas = utils._run('maas-cli maas nodes list')
    maas = MaasState(StringIO(maas.decode('ascii')))
    fpi_tag(maas)
    utils._run('maas-cli maas nodes accept-all')
    name_tag(maas)
    return parse_state(juju, maas)


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
        out = subprocess.check_output(['uvt-kvm', 'list']).decode('utf-8').split('\n')
        return max(map(self.extract_id, out)) + 1 if out else 0

    def find_path(self, hostname):
        vols = subprocess.check_output(['virsh', 'vol-list', 'uvtool']).split('\n')
        for vol in vols:
            if vol.startswith(self.hostname + '.img'):
                return vol.split()[1]
        return None

    def run(self):
        #check_call('startkvm', stdout=DEVNULL, stderr=DEVNULL)

        if not os.path.exists(self.USER_DATA):
            with open(self.MAAS_CREDS) as f:
                [consumer_key, token_key, token_secret] = f.read().strip().split(':')
                with open(self.USER_DATA, 'wb') as f:
                    content = self.CONFIG_TEMPLATE.format(consumer_key=consumer_key,
                                                          token_key=token_key,
                                                          token_secret=token_secret)
                f.write(bytes(content, 'utf-8'))


        hostname = self.SLAVE_PREFIX + str(self.next_host())

        uvt = ['uvt-kvm', 'create', '--bridge', 'br0', hostname]
        subprocess.check_call(uvt)

        # Immediately power off the machine so we can make our edits to its disk.
        # uvt-kvm will support some kind of --no-start option in the future so we don't
        # have to do this.
        subprocess.check_call(['virsh', 'destroy', hostname])


        # Put our cloud-init config in the disk image.
        subprocess.check_call('add_maas_data', find_path(hostname), USER_DATA)

        # Start the machine back up
        subprocess.check_call(['virsh', 'start', hostname])

        subprocess.check_call(['maas-cli', 'maas', 'nodes', 'new', 'hostname=' + hostname])
        creds = os.path.join(tempfile.gettempdir(), 'maas.creds')
        with open(creds, 'wb') as f:
            req = urllib.urlopen(
                'http://localhost/MAAS/metadata/latest/by-id/%s/?op=get_preseed' % (hostname,))
            f.write(req.read())
        subprocess.check_call(['cloud-install', 'maas-signal', '--config', creds, 'OK'])
