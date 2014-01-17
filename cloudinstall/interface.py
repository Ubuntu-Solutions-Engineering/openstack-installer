#
# interface.py - Interface into cloud-installer routines
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

import argparse
import sys

from cloudinstall import roles
from cloudinstall.maas import signal
from cloudinstall.maas.auth import MaasAuth

class App:
    def __init__(self):
        self.args = self.parse_options(sys.argv)
        self.auth = MaasAuth()
    
    def cmd_status(self, options):
        """ Loads Status GUI window
        """
        return roles.Status(self.auth).run()

    def cmd_maas_signal(self, options):
        """ Parses options passed to
            cloud-install maas-signal [opts]
        """
        return signal.parse(options)

    def cmd_maas_creds(self, options):
        """ Parses username for retrieving MAAS user credentials
        """
        api_key = self.auth.get_api_key(options.username)
        if (options.login):
            self.auth.login()
        return api_key

    def parse_options(self, *args, **kwds):
        parser = argparse.ArgumentParser(description='Cloud Installer',
                                         prog='cloud-install')
        subparsers = parser.add_subparsers(title='subcommands',
                                           description='valid subcommands',
                                           help='additional help')

        ########################################################################
        # Cloud services Status
        ########################################################################
        parser_status = subparsers.add_parser('status',
                                              help='Cloud services status')
        parser_status.set_defaults(func=self.cmd_status)

        ########################################################################
        # MAAS signal interface
        ########################################################################
        parser_maas = subparsers.add_parser('maas-signal',
                                            help='MAAS signal interface')
        parser_maas.add_argument("--config", metavar="file",
                                 help="Specify config file", default=None)
        parser_maas.add_argument("--ckey", metavar="key",
                                 help="The consumer key to auth with",
                                 default=None)
        parser_maas.add_argument("--tkey", metavar="key",
                                 help="The token key to auth with",
                                 default=None)
        parser_maas.add_argument("--csec", metavar="secret",
                                 help="The consumer secret (likely '')",
                                 default="")
        parser_maas.add_argument("--tsec", metavar="secret",
                                 help="The token secret to auth with",
                                 default=None)
        parser_maas.add_argument("--apiver", metavar="version",
                                 help="The apiver to use ("" can be used)",
                                 default=signal.MD_VERSION)
        parser_maas.add_argument("--url", metavar="url",
                                 help="The data source to query", default=None)
        parser_maas.add_argument("--file", dest='files',
                                 help="File to post", action='append',
                                 default=[])
        parser_maas.add_argument("--post", dest='posts',
                                 help="name=value pairs to post",
                                 action='append', default=[])
        parser_maas.add_argument("--power-type", dest='power_type',
                                 help="Power type.",
                                 choices=signal.POWER_TYPES,
                                 default=None)
        parser_maas.add_argument("--power-parameters", dest='power_parms',
                                 help="Power parameters.", default=None)
        parser_maas.add_argument("--script-result", metavar="retval", 
                                 type=int, dest='script_result',
                                 help="Return code of a commissioning script.")

        parser_maas.add_argument("status",  help="Status", 
                                 choices=signal.VALID_STATUS,
                                 action='store')
        parser_maas.add_argument("message", help="Optional message",
                                 default="", nargs='?')
        parser_maas.set_defaults(func=self.cmd_maas_signal)

        ########################################################################
        # MAAS user credentials
        ########################################################################
        parser_maas_creds = subparsers.add_parser('maas-creds',
                                                  help='MAAS User credentials')
        parser_maas_creds.add_argument("-u", "--username", metavar="username",
                                       help="Username to get credentials for", 
                                       default='root')
        parser_maas_creds.add_argument("-l", "--login", dest="login",
                                       help="Log into MAAS", action='store_true')

        parser_maas_creds.set_defaults(func=self.cmd_maas_creds)

        return parser.parse_args()

    def run(self):
        self.args.func(self.args)
