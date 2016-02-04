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

import sys
import pytest
import yaml
import requests
from os import path
sys.path.insert(0, '/usr/share/openstack')
from cloudinstall.config import Config  # noqa
from cloudinstall.juju import JujuState  # noqa
from macumba.v1 import JujuClient  # noqa
import cloudinstall.utils as utils  # noqa

CONFIGFILE = path.expanduser("~/.cloud-install/config.yaml")
CONFIGOBJ = yaml.load(utils.slurp(CONFIGFILE))


@pytest.fixture
def juju_state():
    cfg = Config(CONFIGOBJ)
    if not len(cfg.juju_env['state-servers']) > 0:
        state_server = 'localhost:17070'
    else:
        state_server = cfg.juju_env['state-servers'][0]
    juju = JujuClient(
        url=path.join('wss://', state_server),
        password=cfg.juju_api_password)
    juju.login()
    return JujuState(juju)


class TestAutoPilot:

    def test_login_page_accessible(self):
        """ Verifies Autopilot's login page is accessible
        """
        _state = juju_state()
        haproxy = _state.service("haproxy")
        unit = haproxy.unit('haproxy')
        res = requests.get("http://{}/account/standalone/openstack".format(
            unit.public_address), verify=False)
        assert(b"Welcome! - Landscape" in res.content)
