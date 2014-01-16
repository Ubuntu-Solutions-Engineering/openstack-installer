#
# api_helper.py - Helper routines for MAAS API.
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This package is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from oauthlib.oauth1 import SIGNATURE_PLAINTEXT
from requests_oauthlib import OAuth1
import os
import requests
import sys
import time
import urllib
import yaml

__all__ = [
    'geturl',
    'read_config',
    'get_creds'
    ]

def get_creds(username):
    """ Print MAAS user credentials

    @param username: MAAS user to query for credentials
    Original code:
    import sys, os
    sys.path.insert(0, "/usr/share/maas")
    os.environ["DJANGO_SETTINGS_MODULE"] = "maas.settings"
    
    from maasserver.models.user import get_creds_tuple
    from django.contrib.auth.models import User
    from apiclient.creds import convert_tuple_to_string
    
    admin = User.objects.get(username=sys.argv[1])
    token = admin.tokens.all()[0]
    print convert_tuple_to_string(get_creds_tuple(token))
    """
    pass

def read_config(url, creds):
    """Read cloud-init config from given `url` into `creds` dict.

    Updates any keys in `creds` that are None with their corresponding
    values in the config.

    Important keys include `metadata_url`, and the actual OAuth
    credentials.

    @param url: cloud-init config URL
    @param creds: MAAS user credentials
    """
    if url.startswith("http://") or url.startswith("https://"):
        cfg_str = requests.get(url=url).content
    else:
        if url.startswith("file://"):
            url = url[7:]
        cfg_str = open(url, "r").read()

    cfg = yaml.safe_load(cfg_str)

    # Support reading cloud-init config for MAAS datasource.
    if 'datasource' in cfg:
        cfg = cfg['datasource']['MAAS']

    for key in creds.keys():
        if key in cfg and creds[key] == None:
            creds[key] = cfg[key]


def oauth_headers(url, consumer_key, token_key,
                  token_secret, consumer_secret):
    """Build OAuth headers using given credentials.

    @param url: MAAS api endpoint
    @param consumer_key: oauth consumer key
    @param consumer_secret: oauth consumer secret
    @param token_secret: oauth token secret from MAAS Oauth provider
    @param token_key: oauth token key from MAAS Oauth provider
    """
    oauth = OAuth1(consumer_key, 
                   client_secret=consumer_secret, 
                   resource_owner_key=token_key, 
                   resource_owner_secret=token_secret,
                   signature_method=SIGNATURE_PLAINTEXT)
    req = requests.post(url=url, auth=oauth)
    return(req.headers)


def authenticate_headers(url, headers, creds):
    """Update and sign a dict of request headers."""
    if creds.get('consumer_key', None) != None:
        headers.update(oauth_headers(
            url,
            consumer_key=creds['consumer_key'],
            token_key=creds['token_key'],
            token_secret=creds['token_secret'],
            consumer_secret=creds['consumer_secret']
            ))


def warn(msg):
    sys.stderr.write(msg + "\n")


def geturl(url, creds, headers=None, data=None):
    """ Performs a authenticated request against a MAAS endpoint

    @param url: MAAS endpoint
    @param creds: dictionary of OAuth parameters C{oauth_token}, C{oauth_token_secret}
    @param headers: Headers to be passed in with the request
    @param data: extra data sent with the HTTP request
    """
    if headers is None:
        headers = {}
    else:
        headers = dict(headers)

    authenticate_headers(url, headers, creds)
    try:
        req = requests.get(url=url, params=data, headers=headers)
        return req.content
    except requests.execeptions.HTTPError as exc:
        warn(exc.strerror)
