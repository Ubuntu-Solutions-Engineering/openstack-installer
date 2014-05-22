import sys
import unittest
import json

sys.path.insert(0, '../cloudinstall')

from cloudinstall.pegasus import update_machine_info, NOVA_CLOUD_CONTROLLER
from cloudinstall.juju import JujuState
from cloudinstall.maas import MaasState


def test_parse_state():
    with open('test/juju-output/service-pending.out') as juju_file:
        with open('test/maas-output/twonodes.out') as maas_file:
            juju_state = JujuState(juju_file)
            maas_state = MaasState(json.load(maas_file))

            update_machine_info(juju_state, maas_state)

            juju_machines = list(juju_state.machines())

            assert ("node-4c49e73e-e8b8-11e2-ac16-5254002cb1d6"
                    in juju_machines[0].instance_id)
            assert ("node-5fb74ba0-e8c1-11e2-b109-5254002cb1d6"
                    in juju_machines[1].instance_id)

            #assert machines[1]['charms'] == ['mysql']
            #assert machines[1]['units'] == ['mysql/1']
            #assert machines[1]['cpu_count'] == "4"
            #assert machines[1]['memory'] == "8096"
            #assert machines[1]['storage'] == "100.0"


@unittest.skip
def test_lxc():
    with open('test/juju-output/lxc.out') as js:
        with open('test/maas-output/maas-for-lxc.out') as ms:
            juju_state = JujuState(js)
            maas_state = MaasState(json.load(ms))
            update_machine_info(juju_state, maas_state)

            # assert s[2]['machine_no'] == '1/lxc/0'
            # assert s[2]['charms'] == ['mediawiki']
            # assert s[2]['units'] == ['mediawiki/0']


@unittest.skip
def test_lxc_controller_deployed():
    with open('test/juju-output/lxc-controller-deployed.out') as js:
        with open('test/maas-output/maas-for-lxc.out') as ms:
            juju_state = JujuState(js)
            maas_state = MaasState(json.load(ms))
            update_machine_info(juju_state, maas_state)
            assert NOVA_CLOUD_CONTROLLER in juju_state.services
            #assert any([NOVA_CLOUD_CONTROLLER in n.get('charms', []) for n in s])
