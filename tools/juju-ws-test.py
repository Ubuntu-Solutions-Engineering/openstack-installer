#!/usr/bin/env python

from ws4py.client.threadedclient import WebSocketClient
from pprint import pprint
import json
import os
import time

params = {}
params['Type'] = "Admin"
params['Request'] = "Login"
params['RequestId'] = 1
params['Params'] = {"AuthTag": "user-admin",
                    "Password": os.environ['JUJU_PASS']}

msg = None

class Stupid(WebSocketClient):
    def opened(self):
        self.send(json.dumps(params))

    def closed(self, code, reason):
        print(("Closed", code, reason))

    def received_message(self, m):
        print(("Message", json.loads(m.data.decode('utf-8'))))

if __name__ == '__main__':
    ws = Stupid(os.environ['JUJU_URL'], protocols=['https-only'])
    ws.daemon = False
    ws.connect()
    time.sleep(1)
    info = {'Type': 'Client',
            'Request': 'EnvironmentInfo'}
    ws.send(json.dumps(info))
    ws.close()
