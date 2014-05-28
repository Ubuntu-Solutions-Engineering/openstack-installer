#!/usr/bin/env python2

from __future__ import unicode_literals

import argparse
import csv
import json
import gzip
import StringIO
import urlparse
import urllib2

from os.path import expanduser

from apiclient.maas_client import (
    MAASClient,
    MAASDispatcher,
    MAASOAuth,
    )

def get_client(url, creds):
    [consumer_key, token, secret] = creds.split(':')
    auth = MAASOAuth(consumer_key=consumer_key, resource_token=token,
                     resource_secret=secret)
    return MAASClient(auth, MAASDispatcher(), url)

def main():
    with open(expanduser('~/.cloud-install/maas-creds')) as f:
        client = get_client('http://localhost/MAAS/api/1.0/', f.read().strip())

    for mac in ['ec:a8:6b:fc:34:f8', 'ec:a8:6b:fe:15:75', 'ec:a8:6b:fb:34:d6']:
        node_data = {
            'architecture': 'amd64',
            'mac_addresses': [mac],
            'power_type': 'amt',
            'power_parameters_mac_address': mac,
            'power_parameters_power_pass': 'Password1+',
            'nodegroup': '',
        }
        try:
            resp = client.post('nodes/', 'new', **node_data).read()
            print(resp)
            system_id = json.loads(resp)['system_id']
        except urllib2.HTTPError as e:
            try:
                if 'gzip' in e.headers['Content-Encoding']:
                    print(gzip.GzipFile(fileobj=StringIO.StringIO(e.read()), mode='rb').read())
            except KeyError:
                print(e.read())

if __name__ == '__main__':
    main()
