
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


class ConfigException(Exception):
    pass


class Config:
    STYLES = [
        ('body',         'white',      'black',),
        ('header_menu',       'light gray',      'dark gray'),
        ('header_title', 'light gray,bold', 'dark magenta'),
        ('subheading', 'dark gray,bold', 'default'),
        ('focus',        'white',      'dark gray'),
        ('dialog',       'black',      'light gray'),
        ('status_extra',   'light gray,bold',      'dark gray',),
        ('error',        'white',      'dark red'),
        ('info', 'light green', 'default'),
        ('label', 'dark gray', 'default'),
        ('error_icon',    'light red,bold',      'default'),
        ('pending_icon_on',    'light blue,bold',      'default'),
        ('pending_icon',    'dark blue',      'default'),
        ('success_icon',    'light green',      'default'),
        ('button', 'dark blue', 'light gray'),
        ('button_focus', 'light gray', 'dark gray'),
        ('deploy_highlight', 'dark gray', 'light green'),
        ('disabled_button', 'light gray', 'white'),
        ('disabled_button_focus', 'white', 'light gray'),
        ('divider_line', 'light gray', 'default'),
        ('filter', 'dark gray,underline', 'white'),
        ('filter_focus', 'dark gray,underline', 'light gray')
    ]

    def __init__(self):
        self._juju_env = None
        self.node_install_wait_interval = 0.2

    @property
    def tmpl_path(self):
        """ template path """
        return "/usr/share/cloud-installer/templates"

    @property
    def cfg_path(self):
        """ top level configuration path """
        return os.path.expanduser('~/.cloud-install')

    @property
    def is_single(self):
        return os.path.exists(os.path.expanduser('~/.cloud-install/single'))

    @property
    def is_multi(self):
        return os.path.exists(os.path.expanduser('~/.cloud-install/multi'))

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
            env_path = os.path.join(os.path.expanduser('~/.juju/environments'),
                                    env_file)
        else:
            raise ConfigException('Unable to determine installer type.')

        if os.path.exists(env_path):
            with open(env_path) as f:
                self._juju_env = yaml.load(f.read().strip())
            return self._juju_env
        raise ConfigException('Unable to load environments file. Is '
                              'juju bootstrapped?')

    def update_environments_yaml(self, key, val, provider='local'):
        """ updates environments.yaml base file """
        _env_yaml = os.path.expanduser("~/.juju/environments.yaml")
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
            with open(PASSWORD_FILE) as f:
                _password = f.read().strip()
        except IOError:
            _password = 'password'
        return _password
