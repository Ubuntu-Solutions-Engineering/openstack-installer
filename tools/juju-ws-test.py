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
                    "Password": 'pass'}

msg = None


class Stupid(WebSocketClient):
    def opened(self):
        print(('Open', params))
        self.send(json.dumps(params))

    def closed(self, code, reason):
        print(("Closed", code, reason))

    def received_message(self, m):
        pprint(m.data)
        json.loads(m.data.decode('utf-8'))


def cb(shit):
    print(shit)

if __name__ == '__main__':
    ws = Stupid('wss://localhost:17070', protocols=['https-only'])
    ws.daemon = False
    ws.connect()
    time.sleep(1)
    info = {'Type': 'Client',
            'Request': 'FullStatus'}
    ws.send(json.dumps(info))
    ws.close()
