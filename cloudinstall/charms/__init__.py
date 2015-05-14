#
# charms.py - Charm instructions to Cloud Installer
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

import logging
from os import path
import os
import sys
import yaml
from queue import Queue
import subprocess
import time
import requests

from macumba import MacumbaError, ServerError
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
    subordinate = False
    openstack_release_min = 'i'
    depends = []
    conflicts = []
    is_core = False
    contrib = False

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
            try:
                args.append("{}={}".format(k, ','.join(v)))
            except TypeError:
                args.append("{}={}".format(k, v))
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

        have_nextbranch = ['heat', 'nova-cloud-controller',
                           'swift-proxy', 'rabbitmq-server', 'ceph',
                           'swift-storage', 'ceilometer',
                           'ceilometer-agent', 'cinder-ceph',
                           'quantum-gateway', 'openstack-dashboard',
                           'neutron-openvswitch', 'neutron-api',
                           'keystone', 'glance', 'cinder',
                           'nova-compute', 'ceph-osd', 'ceph-radosgw']

        if self.config.getopt('next_charms') and \
           self.charm_name in have_nextbranch:
            self.bzr_get("lp:~openstack-charmers/charms/trusty/{}"
                         "/next".format(self.charm_name))
            self.local_deploy(machine_spec)
            return False

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

    def bzr_get(self, branch_name, series="trusty"):
        """ checkout charms outside of charmstore

        :params str branch_name: bzr repository path,
                eg. lp:~openstack-charmers/charms/trusty/nova-compute
        :params str series: series, defaults trusty
        """
        self.ui.status_info_message("BZR branching '{}'".format(branch_name))
        localrepo = os.path.join(self.config.cfg_path,
                                 'local-charms',
                                 series, self.charm_name)
        os.makedirs(localrepo, exist_ok=True)
        try:
            subprocess.check_output(['bzr', 'co', '--lightweight',
                                     branch_name, localrepo])
        except Exception as e:
            log.warning("error checking out charm: "
                        "rc={} out={}".format(e.returncode,
                                              e.output))
            raise e

    def local_deploy(self, mspec, distro="trusty"):
        localrepo = os.path.join(self.config.cfg_path,
                                 'local-charms')
        kwds = dict(constraints=self.constraints_arg(),
                    repodir=localrepo,
                    charm_name=self.charm_name,
                    distro=distro,
                    mspec=mspec)

        # TODO: See if this is supported by juju api
        juju_home = self.config.juju_home(use_expansion=True)
        cmd = ('{juju_home} juju deploy --repository={repodir}'
               ' local:{distro}/{charm_name}'
               ' --constraints {constraints} '
               '--to {mspec}').format(juju_home=juju_home, **kwds)

        charm_config, _ = get_charm_config()
        if self.charm_name in charm_config:
            cmd += ' --config ' + CHARM_CONFIG_FILENAME

        try:
            infostr = ("Deploying {} from local: {}".format(self.charm_name,
                                                            cmd))
            log.debug(infostr)
            self.ui.status_info_message(infostr)

            cmd_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                                 shell=True)

            log.debug("Deploy output: " + cmd_output.decode('utf-8'))

        except subprocess.CalledProcessError as e:
            log.warning("Deploy error. rc={} out={}".format(e.returncode,
                                                            e.output))
            return True

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

    def __init__(self, ui, config, juju_state=None, juju=None,
                 deployed_charms=None):
        self.charm_post_proc_q = Queue()
        self.is_running = False
        self.ui = ui
        self.config = config
        self.juju = juju
        self.juju_state = juju_state
        if deployed_charms is None:
            self.deployed_charms = []
        else:
            self.deployed_charms = deployed_charms

    def filter_valid_relations(self):
        """
        Return a list of [('relation:interface', 'relation_b:interface')] where
        only charms exist from current deployed_charms.

        Any relation found that is attempting to access a Charm that hasn't
        been deployed will be dropped. We don't error on this because optional
        charms may fall into this category and we want to make sure to include
        those if placed by the controller.
        """
        all_relations = []
        for c in self.deployed_charms:
            all_relations.extend(c.related)

        charm_names = [x.charm_name for x in self.deployed_charms]

        valid_relations = []
        for rel_a, rel_b in all_relations:
            rel_a_svc = rel_a.split(":")[0]
            svc_a_placed = rel_a_svc in charm_names
            rel_b_svc = rel_b.split(":")[0]
            svc_b_placed = rel_b_svc in charm_names

            if svc_a_placed and svc_b_placed:
                valid_relations.append((rel_a, rel_b))
            else:
                msg = ("relation {}:{} ignored "
                       "because:".format(rel_a, rel_b))
                if not svc_a_placed:
                    msg += " {} is not placed".format(rel_a_svc)
                if not svc_b_placed:
                    msg += " {} is not placed".format(rel_b_svc)
                log.info(msg)

        return valid_relations

    @utils.async
    def watch_relations_async(self):
        self.watch_relations()

    def watch_relations(self):
        """ Setup charm relations
        """
        valid_relations = self.filter_valid_relations()
        completed_relations = []
        if len(valid_relations) <= 0:
            return
        log.debug("Processing relations: {}".format(valid_relations))
        while len(valid_relations) != len(completed_relations):
            for relation_a, relation_b in valid_relations:
                try:
                    self.juju.add_relation(relation_a,
                                           relation_b)
                    completed_relations.append((relation_a,
                                                relation_b))
                except ServerError as e:
                    msg = ('Failure in add_relation({}, {}): {}'.format(
                        relation_a,
                        relation_b,
                        e))
                    log.exception(msg)
                    self.ui.status_info_message(msg)
                    raise e

    def _charm_classes(self):
        """ Returns instances of deployed charms """
        charms = []
        for c in self.deployed_charms:
            charm = get_charm(c.charm_name,
                              self.juju,
                              self.juju_state,
                              self.ui,
                              config=self.config)
            charms.append(charm)
        return charms

    @utils.async
    def watch_post_proc_async(self):
        self.watch_post_proc()

    def watch_post_proc(self):
        for charm in self._charm_classes():
            self.charm_post_proc_q.put(charm)

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
