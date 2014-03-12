#!/usr/bin/env python

import os
import sys
sys.path.insert(0, '../cloudinstall')
from cloudinstall.juju.client import JujuClient
from pprint import pprint
import json

JUJU_PASS = os.environ['JUJU_PASS'] if os.environ['JUJU_PASS'] else randomString()
JUJU_URL = os.environ['JUJU_URL'] if os.environ['JUJU_URL'] else 'wss://juju-bootstrap.master:17070/'

if __name__ == '__main__':
    ws = JujuClient(JUJU_URL)
    ws.login(JUJU_PASS)
#    ws.call({'Type':'Client', 'Request': 'EnvironmentInfo'})
    ws.close()
