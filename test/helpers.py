import contextlib
import pegasus

def load_status(fname, cons):
    def wrap(f):
        def new_f():
            with open(fname) as inp:
                return f(cons(inp))
        # copy the name to make nose happy
        new_f.__name__ = f.__name__
        return new_f
    return wrap

def parse_output(name):
    with open('juju-output/%s.out' % name) as juju_out:
        with open('maas-output/%s.out' % name) as maas_out:
            maas = pegasus.MaasState(maas_out)
            juju = pegasus.JujuState(juju_out.read())
            return pegasus.parse_state(juju, maas)

@contextlib.contextmanager
def set_single_system(setting):
    old = pegasus.SINGLE_SYSTEM
    pegasus.SINGLE_SYSTEM = setting
    yield
    pegasus.SINGLE_SYSTEM = old
