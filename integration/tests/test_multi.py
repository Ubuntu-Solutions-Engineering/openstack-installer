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


class TestMulti:
    USERDIR = os.path.expanduser("~/.cloud-install")
    CONFIG = yaml.load(utils.slurp(os.path.join(USERDIR, 'config.yaml')))

    def test_openstack_creds_exist(self):
        """ Verifies OpenStack credential files exist.
        """
        creds = ['openstack-admin-rc', 'openstack-ubuntu-rc']
        for c in creds:
            assert os.path.isfile(os.path.join(self.USERDIR,
                                               c))

    def todo_test_openstack_creds_admin_password(self):
        """ Verifies OpenStack admin password from config yaml
            matches admin password in admin rc file.
        """
        # NOTE(beisner): revisit after https://goo.gl/dPPYcV
        # is resolved.
        pass

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

    def test_juju_stat_enviro_name(self):
        """ Verifies juju stat and enviro name
        """
        cmd = ("JUJU_HOME=~/.cloud-install/juju juju stat --format yaml")
        out = utils.get_command_output(cmd)
        assert('environment: maas' in out['output'])
