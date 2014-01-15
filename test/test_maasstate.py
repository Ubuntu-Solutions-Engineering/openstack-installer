import sys
sys.path.append('../cloudinstall')

from cloudinstall.pegasus import MaasState
import helpers

load_status = lambda f: helpers.load_status(f, MaasState)

@load_status('maas-output/twonodes.out')
def test_twonodes(s):
    assert s.machines == 2
    assert s.num_in_state(MaasState.ALLOCATED) == 1
    assert s.num_in_state(MaasState.READY) == 1
