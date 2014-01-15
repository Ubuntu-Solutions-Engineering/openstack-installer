import sys
sys.path.append('../cloudinstall')

from cloudinstall.pegasus import parse_state, JujuState, MaasState, NOVA_CLOUD_CONTROLLER

def test_poll_state():
    with open('juju-output/service-pending.out') as js:
        with open('maas-output/twonodes.out') as ms:
            s = parse_state(JujuState(js), MaasState(ms))

            assert s[0]['tag'] == "node-4c49e73e-e8b8-11e2-ac16-5254002cb1d6"
            assert 'charm' not in s[0]

            assert s[1]['tag'] == "node-5fb74ba0-e8c1-11e2-b109-5254002cb1d6"
            assert s[1]['charms'] == ['mysql']
            assert s[1]['units'] == ['mysql/1']
            assert s[1]['cpu_count'] == "4"
            assert s[1]['memory'] == "8096"
            assert s[1]['storage'] == "100.0"

def test_lxc():
    with open('juju-output/lxc.out') as js:
        with open('maas-output/maas-for-lxc.out') as ms:
            juju = JujuState(js)
            s = parse_state(juju, MaasState(ms))

            assert s[2]['machine_no'] == '1/lxc/0'
            assert s[2]['charms'] == ['mediawiki']
            assert s[2]['units'] == ['mediawiki/0']

def test_lxc_controller_deployed():
    with open('juju-output/lxc-controller-deployed.out') as js:
        with open('maas-output/maas-for-lxc.out') as ms:
            juju = JujuState(js)
            s = parse_state(juju, MaasState(ms))
            assert NOVA_CLOUD_CONTROLLER in juju.services
            assert any([NOVA_CLOUD_CONTROLLER in n.get('charms', []) for n in s])
