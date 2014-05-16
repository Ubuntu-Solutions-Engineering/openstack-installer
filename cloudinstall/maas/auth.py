#
# auth.py - MAAS Authentication
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from subprocess import check_output, check_call, DEVNULL
import os
import requests
import yaml
import sys
import logging

log = logging.getLogger(__name__)


class MaasAuth:
    """ MAAS Authorization class
    """
    def __init__(self):
        """ Initialize with optional OAuth credentials
        """
        self.api_url = 'http://localhost/MAAS/api/1.0'
        self.api_key = None
        self.consumer_secret = ''

    @property
    def is_logged_in(self):
        """ Checks if we are logged into the MAAS api

        :rtype: bool
        """
        return True if self.api_key else False

    @property
    def consumer_key(self):
        """ Maas consumer key

        :rtype: str
        """
        return self.api_key.split(':')[0] if self.api_key else None

    @property
    def token_key(self):
        """ Maas oauth token key

        :rtype: str
        """
        return self.api_key.split(':')[1] if self.api_key else None

    @property
    def token_secret(self):
        """ Maas oauth token secret

        :rtype: str
        """
        return self.api_key.split(':')[2] if self.api_key else None

    def get_api_key(self, username='root'):
        """ MAAS api key

        :param username: (optional) MAAS user to query for credentials
        :type username: str
        """
        maas_creds_file = os.path.expanduser('~/.cloud-install/maas-creds')
        if os.path.isfile(maas_creds_file):
            with open(maas_creds_file, 'r') as f:
                self.api_key = f.read().rstrip('\n')
        else:
            log.debug("Could not find credentials, attempting to login.")
            out = check_output(['sudo', 'maas-region-admin', 'apikey',
                                '--username', username])
            self.api_key = out.decode('ascii').rstrip('\n')

    def read_config(self, url, creds):
        """Read cloud-init config from given `url` into `creds` dict.

        Updates any keys in `creds` that are None with their corresponding
        values in the config.

        Important keys include `metadata_url`, and the actual OAuth
        credentials.

        :param url: cloud-init config URL
        :type url: str
        :param creds: MAAS user credentials
        :type creds: dict
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
            if key in cfg and creds[key] is None:
                creds[key] = cfg[key]

    def login(self):
        """ Login to MAAS api server

        .. todo::

            Deprecate once MAAS api matures (http://pad.lv/1058137)
        """
        if not self.api_key:
            raise Exception('No api_key was found, please run '
                            '`cloud-install maas-creds -u root`')
            sys.exit(1)

        check_call('sudo maas login maas http://localhost/MAAS/api/1.0 '
                   '%s' % (self.api_key,),
                   shell=True,
                   stderr=DEVNULL,
                   stdout=DEVNULL)
