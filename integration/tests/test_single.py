# Copyright 2015 Canonical, Ltd.
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

import os
import sys
import yaml

sys.path.insert(0, '/usr/share/openstack')
import cloudinstall.utils as utils  # noqa
from cloudinstall.api.container import LXCContainer  # noqa


class TestSingle:
    USERDIR = os.path.expanduser("~/.cloud-install")
    CONFIG = yaml.load(utils.slurp(os.path.join(USERDIR, 'config.yaml')))

    def test_openstack_creds_exist(self):
        """ Verifies OpenStack credential files exist
        """
        creds = ['openstack-admin-rc', 'openstack-ubuntu-rc']
        for c in creds:
            assert os.path.isfile(os.path.join(self.USERDIR,
                                               c))

    def test_bootstrap_succeeded(self):
        """ Verifies a local bootstrap happened
        """
        cmd = ("JUJU_HOME=~/.cloud-install/juju juju stat --format yaml")
        out = LXCContainer.run(self.CONFIG['container_name'],
                               cmd, use_ssh=True)
        out = out.split("\n")[0].strip()
        assert('environment: local' in out)

    def test_container_ip_matches(self):
        """ Verifies container ip in config matches
        what LXC sees
        """
        saved_ip = self.CONFIG['container_ip']
        lxc_ip = LXCContainer.ip(self.CONFIG['container_name'])
        assert saved_ip == lxc_ip

    def test_config_deploy_complete(self):
        """ Verifies config data:  deploy is complete.
        """
        assert self.CONFIG['deploy_complete'] is True

    def test_config_postproc_complete(self):
        """ Verifies config data:  postproc is complete.
        """
        assert self.CONFIG['postproc_complete'] is True

    def test_config_relations_complete(self):
        """ Verifies config data:  relations are complete.
        """
        assert self.CONFIG['relations_complete'] is True
