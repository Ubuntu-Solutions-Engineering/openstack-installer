#
# charms.py - Charm instructions to Cloud Installer
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
import yaml
from os.path import expanduser, exists
import sys
from queue import Queue
import time

from cloudinstall import pegasus, utils
from cloudinstall.juju.client import JujuClient
from cloudinstall.juju import JujuState

log = logging.getLogger('cloudinstall.charms')

CHARM_CONFIG_FILENAME = expanduser("~/.cloud-install/charmconf.yaml")
CHARM_CONFIG = {}
if exists(CHARM_CONFIG_FILENAME):
    with open(CHARM_CONFIG_FILENAME) as f:
        CHARM_CONFIG = yaml.load(f.read())


class CharmBase:
    """ Base charm class """

    charm_name = None
    display_name = None
    related = []
    isolate = False
    constraints = None
    deploy_priority = sys.maxsize
    allow_multi_units = False
    optional = False
    disabled = False

    def __init__(self, juju_state=None, machine=None):
        """ initialize

        :param state: :class:JujuState
        :param machine: :class:Machine
        """
        self.charm_path = None
        self.exposed = False
        self.juju_state = juju_state
        assert isinstance(self.juju_state, JujuState)
        self.machine = machine
        self.client = JujuClient()

    @property
    def is_single(self):
        return pegasus.SINGLE_SYSTEM

    @property
    def is_multi(self):
        return pegasus.MULTI_SYSTEM

    def openstack_password(self):
        PASSWORD_FILE = expanduser('~/.cloud-install/openstack.passwd')
        try:
            with open(PASSWORD_FILE) as f:
                OPENSTACK_PASSWORD = f.read().strip()
        except IOError:
            OPENSTACK_PASSWORD = 'password'
        return OPENSTACK_PASSWORD

    def is_related(self, charm, relations):
        """ test for existence of charm relation

        :param str charm: charm to verify
        :param list relations: related charms
        :returns: True if existing relation found, False otherwise
        :rtype: bool
        """
        try:
            list(filter(lambda r: charm in r.charms,
                        relations))[0]
            return True
        except IndexError:
            return False

    @classmethod
    def name(class_):
        """ Return charm name

        :returns: name of charm
        :rtype: lowercase str
        """
        if class_.charm_name:
            return class_.charm_name
        return class_.__name__.lower()

    def setup(self, _id=None):
        """ Deploy charm and configuration options

        The default should be sufficient but if more functionality
        is needed this should be overridden.
        """
        kwds = {}
        kwds['machine_id'] = _id

        if self.charm_name in CHARM_CONFIG:
            kwds['configfile'] = CHARM_CONFIG_FILENAME

        if self.isolate:
            kwds['machine_id'] = None
            kwds['instances'] = 1
            kwds['constraints'] = self.constraints
            self.client.deploy(self.charm_name, kwds)
        else:
            self.client.deploy(self.charm_name, kwds)

    def set_relations(self):
        """ Setup charm relations

        Override in charm specific.
        """
        if len(self.related) > 0:
            services = self.juju_state.service(self.charm_name)
            for charm in self.related:
                if not self.is_related(charm, services.relations):
                    err = self.client.add_relation(self.charm_name,
                                                   charm)
                    if err:
                        log.error("Relation not ready for "
                                  "{c}, requeueing.".format(c=self.charm_name))
                        return True
        return False

    def post_proc(self):
        """ Perform any post processing

        i.e. setting configuration variables for a charm

        Override in charm classes
        """
        pass

    def __repr__(self):
        return self.name()


class CharmQueue:
    """ charm queue for handling relations in the background
    """
    def __init__(self):
        self.charm_q = Queue()
        self.is_running = False

    def add(self, charm):
        self.charm_q.put(charm)

    @utils.async
    def watch_relations(self):
        log.debug("Starting relations watcher.")
        while True:
            charm = self.charm_q.get()
            err = charm.set_relations()
            if err:
                self.charm_q.put(charm)
            else:
                charm.post_proc()
            self.charm_q.task_done()
            time.sleep(1)
