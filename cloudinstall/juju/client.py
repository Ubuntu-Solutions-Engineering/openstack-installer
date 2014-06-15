#
# client.py - Juju api client
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

# TODO: Make use of python3-websocket once
# https://github.com/liris/websocket-client/pull/76 is merged.
# from ws4py.client.threadedclient import WebSocketClient
# import json
# import time
import logging

from cloudinstall.utils import get_command_output

log = logging.getLogger(__name__)

# class JujuWS(WebSocketClient):
#     def opened(self):
#         creds = {'Type': 'Admin',
#                  'Request': 'Login',
#                  'RequestId': 1,
#                  'Params' : { 'AuthTag' : 'user-admin',
#                               'Password' : self.juju_pass}}
#         self.send(json.dumps(creds))

#     def received_message(self, m):
#         json.loads(m.data.decode('utf-8'))

#     @property
#     def juju_pass(self):
#         return self._juju_pass

#     @juju_pass.setter
#     def juju_pass(self, password):
#         self._juju_pass = password


class JujuClient:
    """ Juju client class """

    def __init__(self, url='wss://juju-bootstrap.maas:17070/'):
        "Constructor. url param is a websocket url, currently unused."
        #     self.conn = JujuWS(url, protocols=['https-only'])
        #     self._request_id = 1
        #     self.is_connected = False

    # def login(self, password):
    #     """ Login to juju

    #     :param password: password of juju websocket api server
    #     """
    #     self.conn.daemon = False
    #     self.conn.juju_pass = password
    #     if not self.is_connected:
    #         self.conn.connect()
    #     time.sleep(1)
    #     self.is_connected = True

    # def close(self):
    #     """ Closes connection to juju websocket """
    #     self.conn.close()

    # def call(self, params):
    #     """ Get json data from juju api daemon

    #     :params params: Additional params to be passed into request
    #     :type params: dict
    #     """
    #     self._request_id = self._request_id + 1
    #     params['RequestId'] = self._request_id
    #     self.conn.send(json.dumps(params))

    # def info(self):
    #     """ Returns Juju environment state """
    #     return self.call(dict(Type="Client",
    #                           Request="EnvironmentInfo"))

    # def add_charm(self, charm_url):
    #     """ Adds charm """
    #     return self.call(dict(Type="Client",
    #                           Request="AddCharm",
    #                           Params=dict(URL=charm_url)))

    # def get_charm(self, charm_url):
    #     """ Get charm """
    #     return self.call(dict(Type='Client',
    #                           Request='CharmInfo',
    #                           Params=dict(CharmURL=charm_url)))

    # def get_env_constraints(self):
    #     """ Get environment constraints """
    #     return self.call(dict(Type="Client",
    #                           Request="GetEnvironmentConstraints"))

    # def set_env_constraints(self, constraints):
    #     """ Set environment constraints """
    #     return self.call(dict(Type="Client",
    #                           Request="SetEnvironmentConstraints",
    #                           Params=constraints))

    # def get_env_config(self):
    #     """ Get environment config """
    #     return self.call(dict(Type="Client",
    #                           Request="EnvironmentGet"))

    # def set_env_config(self, config):
    #     """ Sets environment config variables """
    #     return self.call(dict(Type="Client",
    #                           Request="EnvironmentSet",
    #                           Params=dict(Config=config)))

    def add_machine(self, constraints=None):
        """ Allocate new machine

        :param dict constraints: (optional) machine parameters
        :returns: True on success, False on fail
        :rtype: bool
        """
        cmd = "juju add-machine"
        opts = []
        if constraints:
            log.debug("Setting machine constraints: "
                      "({constraints}), ".format(constraints=constraints))
            for k, v in constraints.items():
                opts.append("{k}={v}".format(k=k, v=v))
            if opts:
                cmd = ("{cmd} --constraints \"{opts}\"".format(
                    cmd=cmd, opts=" ".join(opts)))
        cmd_ = get_command_output(cmd)
        log.debug("Machine added: {cmd} ({out})".format(cmd=cmd,
                                                        out=cmd_['stdout']))
        return cmd_['stdout']

    # def add_machines(self, machines):
    #     """ Add machines """
    #     return self.call(dict(Type="Client",
    #                           Request="AddMachines",
    #                           Params=dict(MachineParams=machines)))

    # def add_relation(self, endpoint_a, endpoint_b):
    #     """ Adds relation between units """
    #     return self.call(dict(Type="Client",
    #                           Request="AddRelation",
    #                           Params=dict(Endpoints=[endpoint_a,
    #                                                  endpoint_b])))
    def add_relation(self, endpoint_a, endpoint_b):
        """ Add relation between services """
        cmd = "juju add-relation {a} {b}".format(a=endpoint_a,
                                                 b=endpoint_b)
        cmd_ = get_command_output(cmd, combine_output=True)
        log.debug("Adding relation ({a},{b}) ".format(a=endpoint_a,
                                                      b=endpoint_b))
        if cmd_['ret']:
            log.error("Result: {r}".format(r=cmd_['stdout']))
            return True
        return False

    # def remove_relation(self, endpoint_a, endpoint_b):
    #     """ Removes relation """
    #     return self.call(dict(Type="Client",
    #                           Request="DestroyRelaiton",
    #                           Params=dict(Endpoints=[endpoint_a,
    #                                                  endpoint_b])))

    # def deploy(self, service_name, charm_url,
    #            num_units=1, config=None,
    #            constraints=None, machine_spec=None):
    #     return self.call(dict(Type="Client",
    #                           Request="ServiceDeploy",
    #                           Params=dict(ServiceName=service_name,
    #                                       CharmURL=charm_url,
    #                                       NumUnits=num_units,
    #                                       Config=config,
    #                                       Constraints=constraints,
    #                                       ToMachineSpec=machine_spec)))
    def deploy(self, charm, settings):
        """ Deploy a charm to an instance

        :param str charm: charm to deploy
        :param str machine_id: (optional) machine id
        :param str instances: (optional) number of instances to deploy
        :param dict constraints: (optional) machine constraints
        """
        cmd = "juju deploy"
        if 'machine_id' in settings and settings['machine_id']:
            cmd += " --to {mid}".format(mid=settings['machine_id'])

        if 'instances' in settings:
            cmd += " -n {instances}".format(instances=settings['instances'])

        if 'configfile' in settings:
            cmd += " --config {file}".format(file=settings['configfile'])

        if 'constraints' in settings:
            opts = []
            for k, v in settings['constraints'].items():
                opts.append("{k}={v}".format(k=k, v=v))
            if opts:
                cmd += " --constraints \"{opts}\"".format(opts=" ".join(opts))

        cmd += " {charm}".format(charm=charm)
        log.debug("Deploying {charm} -> {cmd}".format(charm=charm, cmd=cmd))

        cmd_ = get_command_output(cmd)
        log.debug("Deploy result: {out}".format(out=cmd_['stdout']))
        if cmd_['ret']:
            log.warning("Deploy error ({cmd}): "
                        "{out}".format(cmd=cmd, out=cmd_['stdout']))

    # def set_config(self, service_name, config_keys):
    #     """ Sets machine config """
    #     return self.call(dict(Type="Client",
    #                           Request="ServiceSet",
    #                           Params=dict(ServiceName=service_name,
    #                                       Options=config_keys)))
    def set_config(self, service_name, config_keys):
        """ Set configuration item on service

        :param str service_name: name of service/charm
        :param dict config_keys: config parameters in the
                                 form of { 'key' : 'value' }
        """
        log.debug("Setting config variables for "
                  "{name}".format(name=service_name))
        for k, v in config_keys.items():
            cmd = "juju set {service} {k}={v}".format(service=service_name,
                                                      k=k, v=v)
            cmd_ = get_command_output(cmd)
            if cmd_['ret']:
                log.warning("Problem setting config: "
                            "{out}".format(out=cmd_['stdout']))

    # def unset_config(self, service_name, config_keys):
    #     """ Unsets machine config """
    #     return self.call(dict(Type="Client",
    #                           Request="ServiceUnset",
    #                           Params=dict(ServiceName=service_name,
    #                                       Options=config_keys)))

    # def set_charm(self, service_name, charm_url, force=0):
    #     return self.call(dict(Type="Client",
    #                           Request="ServiceSetCharm",
    #                           Params=dict(ServiceName=service_name,
    #                                       CharmUrl=charm_url,
    #                                       Force=force)))

    # def get_service(self, service_name):
    #     """ Get charm, config, constraits for srevice"""
    #     return self.call(dict(Type="Client",
    #                           Request="ServiceGet",
    #                           Params=dict(ServiceName=service_name)))

    # def get_config(self, service_name):
    #     """ Get service configuration """
    #     svc = self.get_service(service_name)
    #     return svc['Config']

    # def get_constraints(self, service_name):
    #     """ Get service constraints """
    #     return self.call(dict(Type="Client",
    #                           Request="GetServiceConstraints",
    #                           Params=dict(ServiceName=service_name)))

    # def set_constraints(self, service_name, constraints):
    #     """ Sets service level constraints """
    #     return self.call(dict(Type="Client",
    #                           Request="SetServiceConstraints",
    #                           Params=dict(ServiceName=service_name,
    #                                       Constraints=constraints)))

    # def update_service(self, service_name, charm_url, force_charm_url=0,
    #                    min_units=1, settings={}, constraints={}):
    #     """ Update service """
    #     return self.call(dict(Type="Client",
    #                           Request="SetServiceConstraints",
    #                           Params=dict(ServiceName=service_name,
    #                                       CharmUrl=charm_url,
    #                                       MinUnits=min_units,
    #                                       SettingsStrings=settings,
    #                                       Constraints=constraints)))

    # def destroy_service(self, service_name):
    #     """ Destroy a service """
    #     return self.call(dict(Type="Client",
    #                           Request="ServiceDestroy",
    #                           Params=dict(ServiceName=service_name)))

    # def expose(self, service_name):
    #     """ Expose a service """
    #     return self.call(dict(Type="Client",
    #                           Request="ServiceExpose",
    #                           Params=dict(ServiceName=service_name)))

    # def unexpose(self, service_name):
    #     """ Unexpose service """
    #     return self.call(dict(Type="Client",
    #                           Request="ServiceUnexpose",
    #                           Params=dict(ServiceName=service_name)))

    # def valid_relation_name(self, service_name):
    #     """ All possible relation names for service """
    #     return self.call(dict(Type="Client",
    #                           Request="ServiceCharmRelations",
    #                           Params=dict(ServiceName=service_name)))

    # def add_units(self, service_name, num_units=1):
    #     """ Add units """
    #     return self.call(dict(Type="Client",
    #                           Request="AddServiceUnits",
    #                           Params=dict(ServiceName=service_name,
    #                                       NumUnits=num_units)))

    # def add_unit(self, service_name, machine_spec=0):
    #     """ Add unit """
    #     return self.call(dict(Type="Client",
    #                           Request="AddServiceUnits",
    #                           Params=dict(MachineSpec=machine_spec)))
    def add_unit(self, service_name, machine_id=None, count=1):
        """ Add unit to machine

        :param str service_name: service/charm name
        :param str machine_id: machine id
        :param int count: number of units to add
        """
        cmd = "juju add-unit {name}".format(name=service_name)
        if machine_id:
            cmd = "{cmd} --to {_id}".format(cmd=cmd, _id=machine_id)
        if count > 1:
            cmd += " -n {count}".format(count=count)
        log.debug("Adding additional {name}, cmd='{cmd}'".format(
            name=service_name, cmd=cmd))
        cmd_ = get_command_output(cmd)
        if cmd_['ret']:
            log.warning("Problem adding {name} "
                        "{out}".format(name=service_name,
                                       out=cmd_['stdout']))

    # def remove_unit(self, unit_names):
    #     """ Removes unit """
    #     return self.call(dict(Type="Client",
    #                           Request="DestroyServiceUnits",
    #                           Params=dict(UnitNames=unit_names)))

    # def resolved(self, unit_name, retry=0):
    #     """ Resolved """
    #     return self.call(dict(Type="Client",
    #                           Request="Resolved",
    #                           Params=dict(UnitName=unit_name,
    #                                       Retry=retry)))

    # def get_public_address(self, target):
    #     """ Gets public address of instance """
    #     return self.call(dict(Type="Client",
    #                           Request="PublicAddress",
    #                           Params=dict(Target=target)))

    # def set_annontation(self, entity, entity_type, annotation):
    #     """ Sets annontation """
    #     return self.call(dict(Type="Client",
    #                           Request="SetAnnotations",
    #                           Params=dict(Tag="%-%s" % (entity_type, entity),
    #                                       Pairs=annotation)))

    # def get_annotation(self, entity, entity_type):
    #     """ Gets annotation """
    #     return self.call(dict(Type="Client",
    #                           Request="GetAnnotation",
    #                           Params=dict(Tag="%-s%" % (entity_type,
    #                                                     entity))))
