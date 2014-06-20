import sys
import unittest
sys.path.insert(0, '../cloudinstall')

from os.path import expanduser
import urwid

from cloudinstall import gui
from cloudinstall import pegasus
from cloudinstall.juju import JujuState
from cloudinstall.maas import MaasState

import helpers
import mock

DEPLOY_CMD = 'juju deploy --config {p} {{to}}  {{charm}}'.format(p='/tmp/openstack.yaml')
ADD_RELATION = 'juju add-relation {charm1} {charm2}'
REMOVE_UNIT = 'juju remove-unit {unit}'
TERMINATE_MACHINE = 'juju terminate-machine {id}'

# XXX: HACK: For now, all the tests assume that we are in multi-system mode.
pegasus.SINGLE_SYSTEM = False

def fake_metadata(identifier=0):
    metadata = {
        "fqdn": "line %d" % identifier,
        "cpu_count": 1,
        "memory": 2048,
        "storage": 2048,
        "id": "not a unique snowflake",
        "machine_no": 100,
        "agent_state": "pending",
    }
    return metadata

class NonRunningCommandRunner(gui.CommandRunner):
    def _next(self):
        pass

@unittest.skip
def test_ControllerOverlay_process_none():
    o = gui.ControllerOverlay(urwid.Text(""), NonRunningCommandRunner())
    assert o.process([])
    assert len(o.command_runner.to_run) == 1
    assert o.command_runner.to_run[0] == 'juju add-machine'
    assert o.text.get_text()[0] == o.PXE_BOOT

@unittest.skip
def test_ControllerOverlay_process_ready():
    o = gui.ControllerOverlay(urwid.Text(""), NonRunningCommandRunner())
    assert o.process([{'machine_no': '1'}])
    # our hardcoded command above assumes a config, so don't check charms that
    # omit config.
    for charm in filter(lambda c: c not in pegasus._OMIT_CONFIG, pegasus.CONTROLLER_CHARMS):
        cmd = DEPLOY_CMD.format(charm=charm, to="--to lxc:1")
        assert cmd in o.command_runner.to_run, str(cmd) + str(o.command_runner.to_run)
    assert o.text.get_text()[0] == o.NODE_SETUP

@unittest.skip
def test_ControllerOverlay_process_deployed():
    o = gui.ControllerOverlay(urwid.Text(""), NonRunningCommandRunner())
    assert not o.process([{"charms": pegasus.CONTROLLER_CHARMS}])
    assert len(o.command_runner.to_run) == 0
    assert o.done

@unittest.skip
def test_ControllerOverlay__controller_charms_to_allocate():
    with open('juju-output/lxc-controller-deployed.out') as juju_out:
        with open('maas-output/maas-for-lxc.out') as maas_out:
            maas = MaasState(maas_out)
            juju = JujuState(juju_out.read())
            data = pegasus.parse_state(juju, maas)
            over = gui.ControllerOverlay(None, None)
            charms = over._controller_charms_to_allocate(data)
            assert len(charms) == 0

@unittest.skip
def test_Node():
    md = {
        "fqdn": "node",
        "cpu_count": 1,
        "memory": 2048,
        "storage": 2048,
        "id": "not a unique snowflake",
        "machine_no": 100,
        "agent_state": "pending",
        "charms": [pegasus.OPENSTACK_DASHBOARD],
    }
    n = gui.Node(md, lambda: None)
    assert n.is_horizon
    assert n.name == "node"

@unittest.skip
def test_CommandRunner_naked_deploy():
    cr = NonRunningCommandRunner()

    cr.deploy('nova-compute')
    cr.deploy('glance')
    assert cr.to_run[0] == DEPLOY_CMD.format(charm='nova-compute', to="")
    assert cr.to_run[1] == DEPLOY_CMD.format(charm='glance', to="")
    assert cr.to_run[2] == ADD_RELATION.format(charm1='nova-compute', charm2='glance')
    assert len(cr.to_run) == 3

    md = {
        'charms': ['nova-compute', 'glance'],
        'units': ['nova-compute/0', 'glance/0'],
        'machine_no': 0,
    }
    cr.change_allocation(['nova-compute'], md)
    assert cr.to_run[3] == REMOVE_UNIT.format(unit='glance/0')
    cr.change_allocation([], md)
    assert cr.to_run[4] == REMOVE_UNIT.format(unit='nova-compute/0')
    assert cr.to_run[5] == REMOVE_UNIT.format(unit='glance/0')
    assert cr.to_run[6] == TERMINATE_MACHINE.format(id=0), cr.to_run[5]

@unittest.skip
def test_CommandRunner_deploy_to():
    cr = NonRunningCommandRunner()

    cr.deploy(pegasus.NOVA_COMPUTE, id=0)
    cmd = 'juju deploy --config {p} --to 0  nova-compute'.format(
        p=expanduser('/tmp/openstack.yaml'))
    assert cr.to_run[0] == cmd, cr.to_run[0]

@unittest.skip
def test_CommandRunner_deploy_tag():
    cr = NonRunningCommandRunner()

    cr.deploy(pegasus.NOVA_COMPUTE, tag='foo')
    cmd = 'juju deploy --config {p}  --constraints tags=foo nova-compute'.format(
        p='/tmp/openstack.yaml')
    assert cr.to_run[0] == cmd, cr.to_run[0]

@unittest.skip
def test_ControllerOverlay__process_lxc():
    with open('juju-output/lxc-controller-deployed.out') as js:
        with open('maas-output/maas-for-lxc.out') as ms:
            juju = JujuState(js)
            s = pegasus.parse_state(juju, MaasState(ms))
            overlay = gui.ControllerOverlay(None, NonRunningCommandRunner())
            assert not overlay.process(s)

@unittest.skip
def test_NodeViewMode_tick():
    def get_data(foo=[]):
        metadata = fake_metadata(len(foo))
        if len(foo) == 1:
            metadata['charms'] = pegasus.CONTROLLER_CHARMS
        foo.append(metadata)
        return foo

    # a fake MainLoop
    class FakeLoop(object):
        widget = None
        def process_input(self, _unused):
            pass

    nvm = gui.NodeViewMode(FakeLoop(), get_data, NonRunningCommandRunner())

    # fake a maas login, since we're calling nvm directly
    nvm.logged_in = True

    nvm.do_update([])
    assert nvm.target == nvm.controller_overlay
    assert nvm.target.text.get_text()[0] == nvm.target.PXE_BOOT

    nvm.do_update(get_data())
    assert nvm.target == nvm.controller_overlay
    assert nvm.target.text.get_text()[0] == nvm.target.NODE_SETUP

    nvm.do_update(get_data())
    assert nvm.target == nvm
    assert nvm.url.get_text()[0] == 'http://line 1/horizon'


@unittest.skip
def test_allocation():
    with helpers.set_single_system(True):
        result = helpers.parse_output('initial-install-config')
        nrc = NonRunningCommandRunner()
        overlay = gui.ControllerOverlay(None, nrc)
        class FakeStartKVM:
            def run(self):
                pass

        with mock.patch('cloudinstall.pegasus.StartKVM', FakeStartKVM):
            overlay.process(result)

        # we expect all the charms and relations to be added here
        assert len(nrc.to_run) == 14

@unittest.skip
def test_parse_pending_lxcs():
    with helpers.set_single_system(True):
        result = helpers.parse_output('pending')
        assert len(result) == 7
