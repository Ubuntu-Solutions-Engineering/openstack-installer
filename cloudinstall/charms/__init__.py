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
from os import path
import sys
import yaml
from queue import Queue
import time
import requests

from macumba import MacumbaError
from cloudinstall import utils
from cloudinstall.placement.controller import AssignmentType

log = logging.getLogger('cloudinstall.charms')

CHARM_CONFIG_FILENAME = path.expanduser("~/.cloud-install/charmconf.yaml")


def get_charm_config():
    """Returns charm config as python dict and raw yaml, if the file exists.
    Returns {}, None if the file does not exist.
    """
    charm_config = {}
    charm_config_raw = None
    if path.exists(CHARM_CONFIG_FILENAME):
        with open(CHARM_CONFIG_FILENAME) as f:
            charm_config_raw = f.read()
            charm_config = yaml.load(charm_config_raw)
    return charm_config, charm_config_raw


def query_cs(charm, series='trusty'):
    """ This helper routine will query the charm store to pull latest revisions
    and charmstore url for the api.

    :param str charm: charm name
    :param str series: series, defaults. trusty
    """
    charm_store_url = 'https://manage.jujucharms.com/api/3/charm'
    url = path.join(charm_store_url, series, charm)
    r = requests.get(url)
    return r.json()


class DisplayPriorities:

    """A fake enum"""
    Core = 0
    Error = 1
    Compute = 10
    Storage = 20
    Other = 30


def get_charm(charm_name, juju, juju_state, ui, config):
    """ returns single charm class

    :param str charm_name: name of charm to query
    :param juju_state: status of juju
    :rtype: Charm
    :returns: charm class
    """
    for charm in utils.load_charms():
        c = charm.__charm_class__(juju=juju,
                                  juju_state=juju_state,
                                  ui=ui,
                                  config=config)
        if charm_name == c.name():
            return c


class CharmBase:

    """ Base charm class """

    charm_name = None
    charm_rev = None
    display_name = None
    related = []
    isolate = False
    constraints = {}
    deploy_priority = sys.maxsize
    display_priority = DisplayPriorities.Core
    allow_multi_units = False
    allowed_assignment_types = list(AssignmentType)
    disabled = False
    menuable = False
    subordinate = False
    openstack_release_min = 'i'

    def __init__(self, config, ui, juju, juju_state,
                 machine=None):
        """ initialize

        :param state: :class:JujuState
        :param machine: :class:Machine
        """
        self.charm_path = None
        self.exposed = False
        self.machine = machine
        self.juju = juju
        self.juju_state = juju_state
        self.ui = ui
        self.config = config

    def _openstack_env(self, user, password, tenant, auth_url):
        """ setup openstack environment vars """
        return """export OS_USERNAME={user}
export OS_PASSWORD={password}
export OS_TENANT_NAME={tenant}
export OS_AUTH_URL=http://{auth_url}:5000/v2.0
export OS_REGION_NAME=RegionOne
""".format(
            user=user, password=password,
            tenant=tenant, auth_url=auth_url)

    def _openstack_env_save(self, user, data):
        """ sets up environment file user """
        try:
            with open(self._openstack_env_path(user), 'w') as f:
                f.write(data)
        except IOError as e:
            log.error("Unable to write admin environment variables."
                      "(Result: {e})".format(e=e))

    def _openstack_env_path(self, user):
        """ path to openstack environment file """
        fname = "openstack-{u}-rc".format(u=user)
        return path.join(self.config.cfg_path, fname)

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
    def required_num_units(self):
        """Override this in subclasses to force placement of multiple
        units."""
        return 1

    @classmethod
    def name(class_):
        """ Return charm name

        :returns: name of charm
        :rtype: lowercase str
        """
        if class_.charm_name:
            return class_.charm_name
        return class_.__name__.lower()

    def constraints_arg(self):
        """ converts self.constraints into arg form for juju CLI"""
        args = []
        for k, v in self.constraints.items():
            args.append("{}={}".format(k, ','.join(v)))
        all_args = " ".join(args)
        return "\"{}\"".format(all_args)

    def deploy(self, machine_spec, num_units=None):
        """ Deploy charm and configuration options

        The default should be sufficient but if more functionality
        is needed this should be overridden.

        returns True if deploy command was deferred for some reason.
        returns False if no error occurred and deploy command was issued.

        Note that the False (no-error) return value does not indicate
        that service is up and running.
        """
        config_yaml = ""

        _charm_name_rev = self.charm_name

        charm_config, charm_config_raw = get_charm_config()
        log.debug("charm_config = {} ".format(charm_config))
        if self.charm_name in charm_config:
            config_yaml = charm_config_raw

        # Set revision
        if self.charm_rev:
            _charm_name_rev = "{}-{}".format(self.charm_name, self.charm_rev)

        if self.subordinate:
            assert(num_units is None)
            num_units = 0
            assert(len(self.constraints) == 0)
            self.constraints = None
            machine_spec = None
        else:
            if num_units is None:
                num_units = 1

        try:
            # TODO - might not need to pass self.constraints to deploy

            log.debug('calling deploy({}, {}, {}, {}, {}, {})'.format(
                _charm_name_rev, self.charm_name, num_units,
                config_yaml, self.constraints, machine_spec))

            self.juju.deploy(_charm_name_rev, self.charm_name, num_units,
                             config_yaml, self.constraints, machine_spec)
        except MacumbaError:
            log.exception("Error deploying")
            return True

        self.ui.status_info_message("Deployed {0}.".format(self.display_name))
        return False

    def add_unit(self, machine_spec, num_units=1):
        """Add num_units of an already-deployed service onto machine_spec.

        Returns true in case of an error.
        """
        try:
            self.juju.add_unit(self.charm_name, num_units, machine_spec)
        except MacumbaError:
            log.exception("Error adding unit")
            return True
        return False

    def set_relations(self):
        """ Setup charm relations

        Override in charm specific.
        """
        if len(self.related) > 0:
            services = self.juju_state.service(self.charm_name)
            unit = services.unit(self.charm_name)
            if unit.agent_state != "started":
                return True
            for charm in self.related:
                if not self.is_related(charm, services.relations):
                    try:
                        log.debug("calling add_relation({}, {})".format(
                            self.charm_name, charm))
                        self.juju.add_relation(self.charm_name,
                                               charm)
                    except:
                        msg = "Relation {}-{} not ready, " \
                              "requeueing.".format(self.charm_name, charm)
                        log.exception("failure in add_relation {}".format(msg))
                        self.ui.status_info_message(msg)
                        return True
        return False

    def post_proc(self):
        """ Perform any post processing

        i.e. setting configuration variables for a charm

        Override in charm classes
        """
        pass

    def wait_for_agent(self, svcs=None):
        """ Waits for service agent to be reachable

        :param svcs: List of services to check or empty for calling service
        :rtype: Unit()
        :returns: True if all svcs are started, False otherwise
        """
        status_res = []

        if not svcs:
            svcs = [self.charm_name]

        for svc_name in svcs:
            svc = self.juju_state.service(svc_name)
            log.debug("Checking availability for {c}: {s}.".format(
                c=svc_name,
                s=svc))
            unit = svc.unit(svc_name)
            self.ui.status_info_message(
                "Checking availability of {0}: {1}".format(
                    svc_name, unit.agent_state))
            log.debug("Unit state: {}".format(unit.agent_state))
            if unit.agent_state == "started":
                status_res.append(True)
            else:
                status_res.append(False)
        return all(status_res)

    def __repr__(self):
        return self.name()


class CharmQueue:

    """ charm queue for handling relations in the background
    """

    def __init__(self, ui, config):
        self.charm_relations_q = Queue()
        self.charm_deploy_q = Queue()
        self.charm_post_proc_q = Queue()
        self.is_running = False
        self.ui = ui
        self.config = config

    def add_relation(self, charm):
        self.charm_relations_q.put(charm)

    def add_deploy(self, charm):
        self.charm_deploy_q.put(charm)

    def add_post_proc(self, charm):
        self.charm_post_proc_q.put(charm)

    def watch_deploy(self):
        log.debug("Starting charm deploy watcher.")
        while not self.charm_deploy_q.empty():
            try:
                charm = self.charm_deploy_q.get()
                err = charm.deploy()  # TODO call with machine placement
                if err:
                    self.charm_deploy_q.put(charm)
                self.charm_deploy_q.task_done()
            except:
                msg = "Exception in deploy watcher, re-trying."
                log.exception(msg)
                self.ui.status_error_message(msg)
            time.sleep(10)

    @utils.async
    def watch_relations_async(self):
        self.watch_relations()

    def watch_relations(self):
        log.debug("Starting charm relations watcher.")
        while not self.charm_relations_q.empty():
            try:
                charm = self.charm_relations_q.get()
                err = charm.set_relations()
                if err:
                    self.charm_relations_q.put(charm)
                self.charm_relations_q.task_done()
            except:
                msg = "Exception in relations watcher, re-trying."
                log.exception(msg)
                self.ui.status_error_message(msg)
            time.sleep(10)

    @utils.async
    def watch_post_proc_async(self):
        self.watch_post_proc()

    def watch_post_proc(self):
        log.debug("Starting charm post processing watcher.")
        while not self.charm_post_proc_q.empty():
            try:
                charm = self.charm_post_proc_q.get()
                err = charm.post_proc()
                if err:
                    self.charm_post_proc_q.put(charm)
                self.charm_post_proc_q.task_done()
            except:
                msg = "Exception in post-processing watcher, re-trying."
                log.exception(msg)
                self.ui.status_error_message(msg)
            time.sleep(10)
        self.config.setopt('deploy_complete', True)
