import sys
sys.path.append('../src')

import pegasus
import helpers

load_status = lambda f: helpers.load_status(f, pegasus.JujuState)

@load_status('juju-output/no-services.out')
def test_noservices(s):
    assert len(s.assignments) == 0
    assert len(s.services) == 0

@load_status('juju-output/one-pending.out')
def test_onepending(s):
    assert len(s.assignments) == 0
    assert len(s.services) == 0

@load_status('juju-output/service-pending.out')
def test_servicepending(s):
    assert len(s.assignments) == 1
    assert len(s.services) == 1
