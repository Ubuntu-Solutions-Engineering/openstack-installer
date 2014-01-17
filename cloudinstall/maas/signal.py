#
# signal.py - MAAS signal routines
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

import json
import mimetypes
import os.path
import random
import socket
import string
import sys
import urllib

from cloudinstall.maas.client import MaasClient

MD_VERSION = "2012-03-01"
VALID_STATUS = ("OK", "FAILED", "WORKING")
POWER_TYPES = ("ipmi", "virsh", "ether_wake", "moonshot")

def _encode_field(field_name, data, boundary):
    return ('--' + boundary,
            'Content-Disposition: form-data; name="%s"' % field_name,
            '', str(data))


def _encode_file(name, fileObj, boundary):
    return ('--' + boundary,
            'Content-Disposition: form-data; name="%s"; filename="%s"' %
                (name, name),
            'Content-Type: %s' % _get_content_type(name),
            '', fileObj.read())


def _random_string(length):
    return ''.join(random.choice(string.letters) for ii in range(length + 1))


def _get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def encode_multipart_data(data, files):
    """Create a MIME multipart payload from L{data} and L{files}.

    @param data: A mapping of names (ASCII strings) to data (byte string).
    @param files: A mapping of names (ASCII strings) to file objects ready to
        be read.
    @return: A 2-tuple of C{(body, headers)}, where C{body} is a a byte string
        and C{headers} is a dict of headers to add to the enclosing request in
        which this payload will travel.
    """
    boundary = _random_string(30)

    lines = []
    for name in data:
        lines.extend(_encode_field(name, data[name], boundary))
    for name in files:
        lines.extend(_encode_file(name, files[name], boundary))
    lines.extend(('--%s--' % boundary, ''))
    body = '\r\n'.join(lines)

    headers = {'content-type': 'multipart/form-data; boundary=' + boundary,
               'content-length': str(len(body))}

    return body, headers


def fail(msg):
    sys.stderr.write("FAIL: %s" % msg)
    sys.exit(1)

def parse(args):
    """ Parse options passed to it from cli

    @param args: CLI options which are described in 
       C{cloud-install maas-signal help}
    """
    creds = {
        'consumer_key': args.ckey,
        'token_key': args.tkey,
        'token_secret': args.tsec,
        'consumer_secret': args.csec,
        'metadata_url': args.url,
        }

    if args.config:
        MaasAuth().read_config(args.config, creds)

    url = creds.get('metadata_url', None)
    if not url:
        fail("URL must be provided either in --url or in config\n")
    url = "%s/%s/" % (url, args.apiver)

    params = {
        "op": "signal",
        "status": args.status,
        "error": args.message,
        }

    if args.script_result is not None:
        params['script_result'] = args.script_result

    for ent in args.posts:
        try:
            (key, val) = ent.split("=", 2)
        except ValueError:
            sys.stderr.write("'%s' had no '='" % ent)
            sys.exit(1)
        params[key] = val

    if args.power_parms is not None:
        params["power_type"] = args.power_type
        if params["power_type"] == "moonshot":
            user, passwd, address, hwaddress = args.power_parms.split(",")
            power_parms = dict(
                power_user=user,
                power_pass=passwd,
                power_address=address,
                power_hwaddress=hwaddress
                )
        else:
            user, passwd, address = args.power_parms.split(",")
            power_parms = dict(
                power_user=user,
                power_pass=passwd,
                power_address=address
                )
        params["power_parameters"] = json.dumps(power_parms)

    files = {}
    for fpath in args.files:
        files[os.path.basename(fpath)] = open(fpath, "r")

    data, headers = encode_multipart_data(params, files)

    exc = None
    msg = ""

    try:
        payload = MaasAuth().geturl(url, creds=creds, headers=headers, data=data)
        if payload != "OK":
            raise TypeError("Unexpected result from call: %s" % payload)
        else:
            msg = "Success"
    except urllib.error.HTTPError as exc:
        msg = "http error [%s]" % exc.code
    except urllib.error.URLError as exc:
        msg = "url error [%s]" % exc.reason
    except socket.timeout as exc:
        msg = "socket timeout [%s]" % exc
    except TypeError as exc:
        msg = exc.message
    except Exception as exc:
        msg = "unexpected error [%s]" % exc

    sys.stderr.write("%s\n" % msg)
    sys.exit((exc is None))
