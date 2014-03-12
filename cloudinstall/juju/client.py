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

from ws4py.client.threadedclient import WebSocketClient
import json

"""
Example parameters passed to juju:

params = {}
params['Type'] = "Admin"
params['Request'] = 'Login'
params['RequestId'] = 1
params['Params'] = {'AuthTag': 'user-admin',
                    'Password': 'f0d44f279b47cc8b5f7ea291f5e3b30a'}
"""

class JujuWS(WebSocketClient):
    CREDS = ""
    def opened(self):
        self.send(json.dumps(params))

    def closed(self, code, reason):
        print(("Closed", code, reason))

    def received_message(self, m):
        return json.loads(m.data.decode('utf-8'))

class JujuClient:
    """ Juju client class """
    def __init__(self, params, url='juju-bootstrap.master:17070',
                 protocols=['https-only']):
        self.params = params
        self.conn = JujuWS(self.url, protocols=self.protocols)

    def login(self, password):
        self.conn.CREDS = {'Type': 'Admin',
                           'Request': 'Login',
                           'RequestId': 1,
                           'Params' : { 'AuthTag' : 'user-admin',
                                        'Password' : password}}
        self.conn.connect()

    def close(self):
        self.conn.close()

    def call(self, params):
        """ Get json data from juju api daemon """
        return self.conn.send(json.dumps(params))

    def info(self):
        """ Returns Juju environment state """
        return self.call(dict(Type="Client",
                              Request="EnvironmentInfo"))

    def add_charm(self, charm_url):
        """ Adds charm """
        return self.call(dict(Type="Client",
                              Request="AddCharm",
                              Params=dict(URL=charm_url)))

    def get_charm(self, charm_url):
        """ Get charm """
        return self.call(dict(Type='Client',
                              Request='CharmInfo',
                              Params=dict(CharmURL=charm_url)))

    def get_env_constraints(self):
        """ Get environment constraints """
        return self.call(dict(Type="Client",
                              Request="GetEnvironmentConstraints"))

    def set_env_constraints(self, constraints):
        """ Set environment constraints """
        return self.call(dict(Type="Client",
                              Request="SetEnvironmentConstraints",
                              Params=constraints))

    def get_env_config(self):
        """ Get environment config """
        return self.call(dict(Type="Client",
                              Request="EnvironmentGet"))

    def set_env_config(self, config):
        """ Sets environment config variables """
        return self.call(dict(Type="Client",
                              Request="EnvironmentSet",
                              Params=dict(Config=config)))

    def add_machine(self, machine):
        """ Allocate new machine """
        return self.add_machines(machine)

    def add_machines(self, machines):
        """ Add machines """
        return self.call(dict(Type="Client",
                              Request="AddMachines",
                              Params=dict(MachineParams=machines)))

    def add_relation(self, endpoint_a, endpoint_b):
        """ Adds relation between units """
        return self.call(dict(Type="Client",
                              Request="AddRelation",
                              Params=dict(Endpoints=[endpoint_a, endpoint_b])))

    def remove_relation(self, endpoint_a, endpoint_b):
        """ Removes relation """
        return self.call(dict(Type="Client",
                              Request="DestroyRelaiton",
                              Params=dict(Endpoints=[endpoint_a, endpoint_b])))


    def deploy(self, service_name, charm_url,
               num_units=1, config=None,
               constraints=None, machine_spec=None):
        return self.call(dict(Type="Client",
                              Request="ServiceDeploy",
                              Params=dict(ServiceName=service_name,
                                          CharmURL=charm_url,
                                          NumUnits=num_units,
                                          Config=config,
                                          Constraints=constraints,
                                          ToMachineSpec=machine_spec)))

    def set_config(self, service_name, config_keys):
        """ Sets machine config """
        return self.call(dict(Type="Client",
                              Request="ServiceSet",
                              Params=dict(ServiceName=service_name,
                                          Options=config_keys)))

    def unset_config(self, service_name, config_keys):
        """ Unsets machine config """
        return self.call(dict(Type="Client",
                              Request="ServiceUnset",
                              Params=dict(ServiceName=service_name,
                                          Options=config_keys)))

    def set_charm(self, service_name, charm_url, force=0):
        return self.call(dict(Type="Client",
                              Request="ServiceSetCharm",
                              Params=dict(ServiceName=service_name,
                                          CharmUrl=charm_url,
                                          Force=force)))


    def get_service(self, service_name):
        """ Get charm, config, constraits for srevice"""
        return self.call(dict(Type="Client",
                              Request="ServiceGet",
                              Params=dict(ServiceName=service_name)))


    def get_config(self, service_name):
        """ Get service configuration """
        svc = self.get_service(service_name)
        return svc['Config']

    def get_constraints(self, service_name):
        """ Get service constraints """
        return self.call(dict(Type="Client",
                              Request="GetServiceConstraints",
                              Params=dict(ServiceName=service_name)))

    def set_constraints(self, service_name, constraints):
        """ Sets service level constraints """
        return self.call(dict(Type="Client",
                              Request="SetServiceConstraints",
                              Params=dict(ServiceName=service_name,
                                          Constraints=constraints)))

    def update_service(self, service_name, charm_url, force_charm_url=0,
                       min_units=1, settings={}, constraints={}):
        """ Update service """
        return self.call(dict(Type="Client",
                              Request="SetServiceConstraints",
                              Params=dict(ServiceName=service_name,
                                          CharmUrl=charm_url,
                                          MinUnits=min_units,
                                          SettingsStrings=settings,
                                          Constraints=constraints)))

    def destroy_service(self, service_name):
        """ Destroy a service """
        return self.call(dict(Type="Client",
                              Request="ServiceDestroy",
                              Params=dict(ServiceName=service_name)))

    def expose(self, service_name):
        """ Expose a service """
        return self.call(dict(Type="Client",
                              Request="ServiceExpose",
                              Params=dict(ServiceName=service_name)))

    def unexpose(self, service_name):
        """ Unexpose service """
        return self.call(dict(Type="Client",
                              Request="ServiceUnexpose",
                              Params=dict(ServiceName=service_name)))

    def valid_relation_name(self, service_name):
        """ All possible relation names for service """
        return self.call(dict(Type="Client",
                              Request="ServiceCharmRelations",
                              Params=dict(ServiceName=service_name)))

    def add_units(self, service_name, num_units=1):
        """ Add units """
        return self.call(dict(Type="Client",
                              Request="AddServiceUnits",
                              Params=dict(ServiceName=service_name,
                                          NumUnits=num_units)))

    def add_unit(self, service_name, machine_spec=0):
        """ Add unit """
        return self.call(dict(Type="Client",
                              Request="AddServiceUnits",
                              Params=dict(MachineSpec=machine_spec)))

    def remove_unit(self, unit_names):
        """ Removes unit """
        return self.call(dict(Type="Client",
                              Request="DestroyServiceUnits",
                              Params=dict(UnitNames=unit_names)))

    def resolved(self, unit_name, retry=0):
        """ Resolved """
        return self.call(dict(Type="Client",
                              Request="Resolved",
                              Params=dict(UnitName=unit_name,
                                          Retry=retry)))

    def get_public_address(self, target):
        """ Gets public address of instance """
        return self.call(dict(Type="Client",
                              Request="PublicAddress",
                              Params=dict(Target=target)))

    def set_annontation(self, entity, entity_type, annotation):
        """ Sets annontation """
        return self.call(dict(Type="Client",
                              Request="SetAnnotations",
                              Params=dict(Tag="%-%s" % (entity_type, entity),
                                          Pairs=annotation)))

    def get_annotation(self, entity, entity_type):
        """ Gets annotation """
        return self.call(dict(Type="Client",
                              Request="GetAnnotation",
                              Params=dict(Tag="%-s%" % (entity_type, entity))))
