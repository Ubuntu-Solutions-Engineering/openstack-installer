#!/usr/bin/env python

import sys
sys.path.insert(0, '../cloudinstall')
from macumba import JujuClient
from pprint import pprint

JUJU_PASS = 'pass'
JUJU_URL = 'wss://localhost:17070/'

if __name__ == '__main__':
    ws = JujuClient(url=JUJU_URL, password=JUJU_PASS)
    ws.login()
    t = ws.status()
    pprint(t)
    #ws.add_machine()
    # ws.deploy('mysql')
    # ws.deploy('wordpress', dict(charm_url='cs:precise/wordpress-24'))
    # ws.deploy('juju-gui')
    #
    # ws.add_relation('mysql', 'wordpress')
    # ws.add_unit('mysql')
    ws.close()
