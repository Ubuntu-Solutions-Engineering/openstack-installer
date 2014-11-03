
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

import os
import yaml
import json
from cloudinstall import utils


class ConfigException(Exception):
    pass


class Config:
    STYLES = [
        ('body', 'white', 'black'),
        ('header_menu', 'light gray', 'dark gray'),
        ('header_title', 'light gray,bold', 'dark magenta'),
        ('subheading', 'dark gray,bold', 'default'),
        # TODO MERGE: item marked 'from head' are changed in master vs
        # head and need to be reviewed. the uncommented versions of
        # these three are as they were in master, below

        # from head: ('dialog',       'black',      'light gray'),
        # from head: ('button', 'dark blue', 'light gray'),
        # from head: ('button_focus', 'light gray', 'dark gray'),
        ('deploy_highlight_start', 'dark gray', 'light green'),
        ('deploy_highlight_end', 'dark gray', 'dark green'),
        ('disabled_button', 'black', 'white'),
        ('disabled_button_focus', 'black', 'light gray'),
        ('divider_line', 'light gray', 'default'),
        ('filter', 'dark gray,underline', 'white'),
        ('filter_focus', 'dark gray,underline', 'light gray'),
        ('focus', 'white', 'dark gray'),
        ('radio focus', 'white,bold', 'dark magenta'),
        ('input', 'white', 'dark gray'),
        ('input focus', 'dark magenta,bold', 'dark gray'),
        ('dialog', 'white', 'dark gray'),
        ('status_extra', 'light gray,bold', 'dark gray'),
        ('error', 'white', 'dark red'),
        ('info', 'light green', 'default'),
        ('label', 'dark gray', 'default'),
        ('error_icon', 'light red,bold', 'default'),
        ('pending_icon_on', 'light blue,bold', 'default'),
        ('pending_icon', 'dark blue', 'default'),
        ('success_icon', 'light green', 'default'),
        ('button', 'white', 'dark gray'),
        ('button focus', 'dark magenta,bold', 'dark gray')
    ]

    def __init__(self):
        self._juju_env = None
        self.node_install_wait_interval = 0.2

    @property
    def install_types(self):
        """ Installer types
        """
        return ['Single', 'Multi', 'Multi with existing MAAS', 'Landscape']

    @property
    def share_path(self):
        """ base share path
        """
        return "/usr/share/openstack"

    @property
    def tmpl_path(self):
        """ template path """
        return os.path.join(self.share_path, "templates")

    @property
    def cfg_path(self):
        """ top level configuration path """
        return os.path.join(utils.install_home(), '.cloud-install')

    @property
    def bin_path(self):
        """ scripts located in non-default system path """
        return os.path.join(self.share_path, "bin")

    @property
    def placements_filename(self):
        return os.path.join(self.cfg_path, 'placements.yaml')

    @property
    def is_single(self):
        return os.path.exists(os.path.join(self.cfg_path, 'single'))

    @property
    def is_multi(self):
        return os.path.exists(os.path.join(self.cfg_path, 'multi'))

    @property
    def is_landscape(self):
        return os.path.exists(os.path.join(self.cfg_path, 'landscape'))

    @property
    def juju_path(self):
        return os.path.join(utils.install_home(), '.juju')

    @property
    def juju_env(self):
        """ parses current juju environment """
        if self._juju_env:
            return self._juju_env

        env_file = None
        if self.is_single:
            env_file = 'local.jenv'

        if self.is_multi:
            env_file = 'maas.jenv'

        if env_file:
            env_path = os.path.join(utils.install_home(),
                                    '.juju/environments',
                                    env_file)
        else:
            raise ConfigException('Unable to determine installer type.')

        if os.path.exists(env_path):
            with open(env_path) as f:
                self._juju_env = yaml.load(f.read().strip())
            return self._juju_env
        raise ConfigException('Unable to load environments file. Is '
                              'juju bootstrapped?')

    @property
    def juju_environments_path(self):
        """ returns absolute path of juju environments.yaml """
        return os.path.join(self.juju_path, 'environments.yaml')

    def update_environments_yaml(self, key, val, provider='local'):
        """ updates environments.yaml base file """
        _env_yaml = os.path.join(utils.install_home(),
                                 ".juju/environments.yaml")
        if os.path.exists(_env_yaml):
            with open(_env_yaml) as f:
                _env_yaml_raw = f.read()
                env_yaml = yaml.load(_env_yaml_raw)
        else:
            raise ConfigException("~/.juju/environments.yaml unavailable, "
                                  "is juju bootstrapped?")
        if key in env_yaml['environments'][provider]:
            env_yaml['environments'][provider][key] = val
        with open(_env_yaml, 'w') as f:
            _env_yaml_raw = yaml.safe_dump_all(env_yaml)
            f.write(_env_yaml_raw)

    @property
    def juju_api_password(self):
        return self.juju_env['password']

    @property
    def openstack_password(self):
        PASSWORD_FILE = os.path.join(self.cfg_path, 'openstack.passwd')
        try:
            _password = utils.slurp(PASSWORD_FILE)
        except IOError:
            _password = 'password'
        return _password

    def save_password(self, password):
        PASSWORD_FILE = os.path.join(self.cfg_path, 'openstack.passwd')
        utils.spew(PASSWORD_FILE, password)

    def save_maas_creds(self, api_host, api_key):
        """ Saves maas credentials for re-use

        :param str api_host: ip of maas server
        :param str api_key: api key of maas admin user
        """
        if api_host.startswith("http://"):
            raise ConfigException("save_maas_creds expects an ip, not a url")
        MAAS_CREDS_FILE = os.path.join(self.cfg_path, 'maascreds')
        utils.spew(MAAS_CREDS_FILE, json.dumps(dict(api_host=api_host,
                                                    api_key=api_key)))

    @property
    def maas_creds(self):
        """ reads maascreds file
        """
        MAAS_CREDS_FILE = os.path.join(self.cfg_path, 'maascreds')
        try:
            _maascreds = json.loads(utils.slurp(MAAS_CREDS_FILE))
        except IOError:
            _maascreds = dict()
        return _maascreds

    def save_landscape_creds(self, admin_name, admin_email,
                             system_email, maas_server, maas_apikey):
        """ Saves landscape credentials for re-use

        :param str admin_name: admin name
        :param str admin_email: admin email
        :param str system_email: system_email
        :param str maas_server: ip of maas server
        :param str maas_apikey: api key of maas admin user
        """
        LANDSCAPE_CREDS_FILE = os.path.join(self.cfg_path, 'landscapecreds')
        utils.spew(LANDSCAPE_CREDS_FILE,
                   json.dumps(dict(admin_name=admin_name,
                                   admin_email=admin_email,
                                   system_email=system_email,
                                   maas_server=maas_server,
                                   maas_apikey=maas_apikey)))

    @property
    def landscape_creds(self):
        """ reads landscape creds file
        """
        LANDSCAPE_CREDS_FILE = os.path.join(self.cfg_path, 'landscapecreds')
        try:
            _creds = json.loads(utils.slurp(LANDSCAPE_CREDS_FILE))
        except IOError:
            _creds = dict()
        return _creds
