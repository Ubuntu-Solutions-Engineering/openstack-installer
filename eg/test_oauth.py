#!/usr/bin/env python3
#
# usage:
# $ maas apikey <user>
# $ ./test_oauth
#
# result:
# should be a list of tags
#
# actual:
# bad signature

from requests_oauthlib import OAuth1
import requests
from subprocess import check_output, DEVNULL

api_endpoint = 'http://localhost/MAAS/api/1.0/tags'

def get_api_key(username):
    api_key = check_output(['sudo',
                            'maas',
                            'apikey',
                            '--username',
                            username]).decode('ascii').rstrip('\n')
    print("API Key: %s" % (api_key,))
    return api_key

def new_tag():
    tag = 'a-new-new-tag'
    api_key = get_api_key('admin')
    params = dict(op='new',name=tag)
    consumer_key, token_key, token_secret = api_key.split(':')
    oauth = OAuth1(consumer_key, 
                   client_secret='', 
                   resource_owner_key=token_key, 
                   resource_owner_secret=token_secret,
                   signature_method='PLAINTEXT',
                   signature_type='query')
    return requests.post(url=api_endpoint, auth=oauth, params=params)

if __name__ == '__main__':
    print("Start oauth")
    res = new_tag()
    print("URL: %s" % (res.request.url,))
    print(res.ok)
    print(res.text)
    
# (not working)
# Start oauth
# API Key: XBSkAyVSPxpPaJ87GP:KxqXSMPksS6g2SenxZ:xwmLuusNVj3jMuhBdS5XXSnarSPZU4eq
# URL: http://localhost/MAAS/api/1.0/tags/?name=a-new-new-tag&op=new&oauth_nonce=60618171148610572791389994066&oauth_timestamp=1389994066&oauth_version=1.0&oauth_signature_method=PLAINTEXT&oauth_consumer_key=XBSkAyVSPxpPaJ87GP&oauth_token=KxqXSMPksS6g2SenxZ&oauth_signature=%26xwmLuusNVj3jMuhBdS5XXSnarSPZU4eq
# False
# Unrecognised signature: GET new
