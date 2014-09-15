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

from collections import defaultdict

from cloudinstall.machine import satisfies
from cloudinstall.utils import load_charms


class PlacementController:
    """Keeps state of current machines and their assigned services.
    """

    def __init__(self, maas_state, opts):
        self.maas_state = maas_state
        self.assignments = defaultdict(list)  # instance_id -> [charm class]
        self.opts = opts
        self.unplaced_services = set()

    def machines(self):
        return self.maas_state.machines()

    def charm_classes(self):
        cl = [m.__charm_class__ for m in load_charms()
              if not m.__charm_class__.optional and
              not m.__charm_class__.disabled]

        if self.opts.enable_swift:
            for m in load_charms():
                n = m.__charm_class__.name()
                if n == "swift-storage" or n == "swift-proxy":
                    cl.append(m.__charm_class__)
        return cl

    def are_assignments_equivalent(self, other):
        for mid, cl in self.assignments.items():
            if mid not in other:
                return False
            if set(cl) != set(other[mid]):
                return False
        return True

    def assign(self, machine, charm_class):
        if not charm_class.allow_multi_units:
            for m, l in self.assignments.items():
                if charm_class in l:
                    l.remove(charm_class)
        self.assignments[machine.instance_id].append(charm_class)
        self.reset_unplaced()

    def machines_for_charm(self, charm_class):
        all_machines = self.machines()
        machines = []
        for m_id, assignment_list in self.assignments.items():
            if charm_class in assignment_list:
                m = next((m for m in all_machines
                          if m.instance_id == m_id), None)
                if m:
                    machines.append(m)
        return machines

    def remove_assignment(self, m, cc):
        assignments = self.assignments[m.instance_id]
        assignments.remove(cc)
        self.reset_unplaced()

    def clear_all_assignments(self):
        self.assignments = defaultdict(list)
        self.reset_unplaced()

    def clear_assignments(self, m):
        del self.assignments[m.instance_id]
        self.reset_unplaced()

    def assignments_for_machine(self, m):
        return self.assignments[m.instance_id]

    def set_all_assignments(self, assignments):
        self.assignments = assignments
        self.reset_unplaced()

    def reset_unplaced(self):
        self.unplaced_services = set()
        for cc in self.charm_classes():
            ms = self.machines_for_charm(cc)
            if len(ms) == 0:
                self.unplaced_services.add(cc)

    def service_is_core(self, cc):
        uncore_services = ['swift-storage',
                           'swift-proxy',
                           'nova-compute',
                           'juju-gui']
        return cc.name() not in uncore_services

    def can_deploy(self):
        unplaced_cores = [cc for cc in self.unplaced_services
                          if self.service_is_core(cc)]

        return len(unplaced_cores) == 0

    def autoplace_unplaced_services(self):
        """Attempt to find machines for all unplaced services using only empty
        machines.

        Returns a pair (success, message) where success is True if all
        services are placed. message is an info message for the user.
        """

        empty_machines = [m for m in self.machines()
                          if len(self.assignments[m.instance_id]) == 0]

        unplaced_defaults = self.gen_defaults(list(self.unplaced_services),
                                              empty_machines)

        for mid, charm_classes in unplaced_defaults.items():
            self.assignments[mid] = charm_classes

        self.reset_unplaced()

        if len(self.unplaced_services) > 0:
            msg = ("Not enough empty machines could be found for the required"
                   " services. Please add machines or finish placement "
                   "manually.")
            return (False, msg)
        return (True, "")

    def gen_defaults(self, charm_classes=None, maas_machines=None):
        """Generates an assignments dictionary for the given charm classes and
        machines, based on constraints.

        Does not alter controller state.

        Use set_all_assignments(gen_defaults()) to clear and reset the
        controller's state to these defaults.

        """
        if charm_classes is None:
            charm_classes = self.charm_classes()

        assignments = defaultdict(list)

        if maas_machines is None:
            maas_machines = self.maas_state.machines()

        def satisfying_machine(constraints):
            for machine in maas_machines:
                if satisfies(machine, constraints)[0]:
                    maas_machines.remove(machine)
                    return machine

            return None

        isolated_charms, controller_charms = [], []

        for charm_class in charm_classes:
            if charm_class.isolate:
                isolated_charms.append(charm_class)
            else:
                controller_charms.append(charm_class)

        for charm_class in isolated_charms:
            m = satisfying_machine(charm_class.constraints)
            if m:
                assignments[m.instance_id].append(charm_class)

        controller_machine = satisfying_machine({})
        if controller_machine:
            for charm_class in controller_charms:
                assignments[controller_machine.instance_id].append(charm_class)

        return assignments
