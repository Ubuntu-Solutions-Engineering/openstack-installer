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

from collections import defaultdict, Counter
from enum import Enum
import logging
from multiprocessing import cpu_count

from cloudinstall.maas import (satisfies, MaasMachineStatus)
from cloudinstall.utils import load_charms

log = logging.getLogger('cloudinstall.placement')


class AssignmentType(Enum):
    BareMetal = 1
    KVM = 2
    LXC = 3

DEFAULT_SHARED_ASSIGNMENT_TYPE = AssignmentType.LXC


class PlaceholderMachine:

    """A dummy machine that doesn't map to an existing maas machine, to be
    used for single installs only."""

    def __init__(self, instance_id, name, constraints):
        self.instance_id = instance_id
        self.system_id = instance_id
        self.machine_id = -1
        self.display_name = name
        self.constraints = constraints

    @property
    def machine(self):
        return self.constraints

    @property
    def arch(self):
        return self.constraints['arch']

    @property
    def cpu_cores(self):
        return self.constraints['cpu_cores']

    @property
    def mem(self):
        return self.constraints['mem']

    @property
    def storage(self):
        return self.constraints['storage']

    @property
    def hostname(self):
        return self.display_name

    def __repr__(self):
        return "<Placeholder Machine: {}>".format(self.display_name)


class PlacementError(Exception):

    "Generic exception class for placement related errors"


class PlacementController:

    """Keeps state of current machines and their assigned services.
    """

    def __init__(self, maas_state=None, config=None):
        self.config = config
        self.maas_state = maas_state
        self._machines = []
        # id -> {atype: [charm class]}
        self.assignments = defaultdict(lambda: defaultdict(list))
        self.unplaced_services = set()

    def save(self):
        """ Save placement state, to be re-read by
        load(). No guarantees made about the contents of the file.
        """
        flat_assignments = {}
        for iid, ad in self.assignments.items():
            constraints = {}
            if self.maas_state is None:
                machine = next((m for m in self.machines() if
                                m.instance_id == iid), None)
                if machine:
                    constraints = machine.constraints

            flat_ad = {}
            for atype, al in ad.items():
                flat_al = [cc.charm_name for cc in al]
                flat_ad[atype.name] = flat_al

            flat_assignments[iid] = dict(constraints=constraints,
                                         assignments=flat_ad)
        self.config.setopt('placements', flat_assignments)

    def load(self):
        """
        Load assignments from config placements replaces current
        assignments.
        """
        def find_charm_class(name):
            for cc in self.charm_classes():
                if cc.charm_name == name:
                    return cc
            log.warning("Could not find charm class "
                        "matching saved charm name {}".format(name))
            return None

        file_assignments = self.config.getopt('placements')
        new_assignments = defaultdict(lambda: defaultdict(list))
        for iid, d in file_assignments.items():
            if self.maas_state is None:
                constraints = d['constraints']
                pm = PlaceholderMachine(iid, iid,
                                        constraints)
                self._machines.append(pm)
            for atypestr, al in d['assignments'].items():
                new_al = [find_charm_class(ccname)
                          for ccname in al]
                new_al = [x for x in new_al if x is not None]
                at = AssignmentType.__members__[atypestr]
                new_assignments[iid][at] = new_al

        self.assignments.clear()
        self.assignments.update(new_assignments)
        self.reset_unplaced()

    def update_and_save(self):
        self.reset_unplaced()
        self.save()

    def machines(self):
        if self.maas_state:
            return self.maas_state.machines()
        else:
            return self._machines

    def machines_used(self):
        ms = []
        for m in self.machines():
            if m.instance_id in self.assignments:
                n = sum(len(cl) for _, cl in
                        self.assignments[m.instance_id].items())
                if n > 0:
                    ms.append(m)
        return ms

    def charm_classes(self):
        cl = [m.__charm_class__ for m in load_charms()
              if not m.__charm_class__.disabled]

        return cl

    def placed_charm_classes(self):
        "Returns a deduplicated list of all charms that have a placement"
        return [cc for cc in self.charm_classes()
                if cc not in self.unplaced_services]

    def assign(self, machine, charm_class, atype):
        if not charm_class.allow_multi_units:
            for m, d in self.assignments.items():
                for at, l in d.items():
                    if charm_class in l:
                        l.remove(charm_class)

        self.assignments[machine.instance_id][atype].append(charm_class)
        self.update_and_save()

    def machines_for_charm(self, charm_class):
        """ returns assignments for a given charm
        returns {assignment_type : [machines]}
        """
        all_machines = self.machines()
        machines_by_atype = defaultdict(list)
        for m_id, d in self.assignments.items():
            for atype, assignment_list in d.items():
                for a in assignment_list:
                    if a == charm_class:
                        m = next((m for m in all_machines
                                  if m.instance_id == m_id), None)
                        if m:
                            machines_by_atype[atype].append(m)
        return machines_by_atype

    def clear_all_assignments(self):
        self.assignments = defaultdict(lambda: defaultdict(list))
        self.update_and_save()

    def clear_assignments(self, m):
        """clears all assignments for machine m.
        If m has no assignments, does nothing.
        """
        if m.instance_id not in self.assignments:
            return

        del self.assignments[m.instance_id]
        self.update_and_save()

    def remove_one_assignment(self, m, cc):
        ad = self.assignments[m.instance_id]
        for atype, assignment_list in ad.items():
            if cc in assignment_list:
                assignment_list.remove(cc)
                break
        self.update_and_save()

    def assignments_for_machine(self, m):
        """Returns all assignments for given machine

        {assignment_type: [charm_class]}
        """
        return self.assignments[m.instance_id]

    def is_assigned(self, charm_class, machine):
        assignment_dict = self.assignments[machine.instance_id]
        for atype, charm_classes in assignment_dict.items():
            if charm_class in charm_classes:
                return True
        return False

    def set_all_assignments(self, assignments):
        self.assignments = assignments
        self.update_and_save()

    def reset_unplaced(self):
        self.unplaced_services = set()
        for cc in self.charm_classes():
            md = self.machines_for_charm(cc)
            is_placed = False
            for atype, ml in md.items():
                if len(ml) > 0:
                    is_placed = True
            if not is_placed:
                self.unplaced_services.add(cc)

    def service_is_required(self, cc):
        """Returns True if service needs to be placed before deploying is
        OK.
        """
        self.reset_unplaced()
        if cc.name() == 'nova-compute' \
           and cc in self.unplaced_services:
            return True

        unrequired_services = ['nova-compute',
                               'juju-gui']

        storage_backend = self.config.getopt('storage_backend')

        # if we place one of swift-proxy or swift-storage, we must
        # place the others.
        unplaced_services_names = [c.name() for c in
                                   self.unplaced_services]
        swift_charmnames = ['swift-storage', 'swift-proxy']
        ceph_charmnames = ['ceph', 'ceph-osd']

        # if both swift charms are unplaced, then they are unrequired.
        if set(swift_charmnames).issubset(unplaced_services_names) \
           and storage_backend != 'swift':
            unrequired_services += swift_charmnames

        if not storage_backend or storage_backend == 'swift':
            # ceph is required if ceph-osd is placed, but not vice versa.
            if set(ceph_charmnames).issubset(unplaced_services_names):
                unrequired_services += ['ceph', 'ceph-osd']
            else:
                unrequired_services += ['ceph-osd']
        else:
            # ceph was chosen, and is required, but ceph-osd is not required.
            unrequired_services += ['ceph-osd']

        if cc.name() in unrequired_services:
            return False

        n_required = cc.required_num_units()
        # sanity check:
        if n_required > 1 and not cc.allow_multi_units:
            log.error("Inconsistent charm definition for {}:"
                      " - requires {} units but does not allow "
                      "multi units.".format(cc.charm_name, n_required))

        n_units = self.machine_count_for_charm(cc)
        return n_units < n_required

    def can_deploy(self):
        unplaced_requireds = [cc for cc in self.unplaced_services
                              if self.service_is_required(cc)]

        return len(unplaced_requireds) == 0

    def machine_count_for_charm(self, cc):
        """Returns the total number of placements of any type for a given
        charm."""
        return sum([len(al) for al in self.machines_for_charm(cc).values()])

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

        self.update_and_save()

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

        Should not be used for single installs, see gen_single.
        """
        if self.maas_state is None:
            raise PlacementError("Can't call gen_defaults with no maas_state")

        if charm_classes is None:
            charm_classes = self.charm_classes()

        assignments = defaultdict(lambda: defaultdict(list))

        if maas_machines is None:
            maas_machines = self.maas_state.machines(MaasMachineStatus.READY)

        def satisfying_machine(constraints):
            for machine in maas_machines:
                if satisfies(machine, constraints)[0]:
                    maas_machines.remove(machine)
                    return machine

            return None

        isolated_charms, controller_charms = [], []

        for charm_class in self.filter_storage_backends(charm_classes):
            if charm_class.isolate:
                isolated_charms.append(charm_class)
            else:
                controller_charms.append(charm_class)

        for charm_class in isolated_charms:
            for n in range(charm_class.required_num_units()):
                m = satisfying_machine(charm_class.constraints)
                if m:
                    l = assignments[m.instance_id][AssignmentType.BareMetal]
                    l.append(charm_class)

        controller_machine = satisfying_machine({})
        if controller_machine:
            for charm_class in controller_charms:
                ad = assignments[controller_machine.instance_id]
                l = ad[DEFAULT_SHARED_ASSIGNMENT_TYPE]
                l.append(charm_class)

        import pprint
        log.debug(pprint.pformat(assignments))
        return assignments

    def filter_storage_backends(self, charm_classes):
        "return list of charm classes with only selected backends"
        all_backend_charms = ['swift-proxy', 'swift-storage',
                              'ceph']

        selected_backend = self.config.getopt('storage_backend')
        to_remove = all_backend_charms

        if selected_backend:
            to_remove = [n for n in to_remove if
                         selected_backend not in n]

        # ceph-osd is never required, only included for scale-out:
        to_remove.append('ceph-osd')

        log.debug("to_remove is {}".format(to_remove))

        return [cc for cc in charm_classes
                if cc.charm_name not in to_remove]

    def gen_single(self):
        """Generates an assignment for the single installer."""
        assignments = defaultdict(lambda: defaultdict(list))

        max_cpus = cpu_count()
        if max_cpus >= 2:
            max_cpus = max_cpus // 2

        controller = PlaceholderMachine('controller', 'controller',
                                        {'mem': 6144,
                                         'root-disk': 20480,
                                         'cpu-cores': max_cpus})
        self._machines.append(controller)

        charm_name_counter = Counter()

        def placeholder_for_charm(charm_class):
            mnum = charm_name_counter[charm_class.charm_name]
            charm_name_counter[charm_class.charm_name] += 1

            instance_id = '{}-machine-{}'.format(charm_class.charm_name,
                                                 mnum)
            m_name = 'machine {} for {}'.format(mnum,
                                                charm_class.display_name)

            return PlaceholderMachine(instance_id, m_name,
                                      charm_class.constraints)

        for charm_class in self.filter_storage_backends(self.charm_classes()):
            if charm_class.isolate:
                for n in range(charm_class.required_num_units()):
                    pm = placeholder_for_charm(charm_class)
                    self._machines.append(pm)
                    ad = assignments[pm.instance_id]
                    # in single, "BareMetal" is in a KVM on the host
                    ad[AssignmentType.BareMetal].append(charm_class)
            else:
                ad = assignments[controller.instance_id]
                ad[AssignmentType.LXC].append(charm_class)

        import pprint
        log.debug("gen_single() = '{}'".format(pprint.pformat(assignments)))
        return assignments
