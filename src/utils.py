from subprocess import Popen, PIPE, DEVNULL, call
from contextlib import contextmanager

# String with number of minutes, or None.
blank_len = None

def partition(pred, iterable):
    yes, no = [], []
    for i in iterable:
        (yes if pred(i) else no).append(i)
    return (yes, no)

# TODO: replace with check_output()
def _run(cmd):
    return Popen(cmd.split(), stdout=PIPE, stderr=DEVNULL).communicate()[0]

def reset_blanking():
    global blank_len
    if blank_len is not None:
        call(('setterm', '-blank', blank_len))

@contextmanager
def console_blank():
    global blank_len
    try:
        with open('/sys/module/kernel/parameters/consoleblank') as f:
            blank_len = f.read()
    except (IOError, FileNotFoundError):
        blank_len = None
    else:
        # Cannot use anything that captures stdout, because it is needed
        # by the setterm command to write to the console.
        call(('setterm', '-blank', '0'))
        # Convert the interval from seconds to minutes.
        blank_len = str(int(blank_len)//60)

    yield

    reset_blanking()
