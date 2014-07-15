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
        ('border',       'brown',      'dark magenta'),
        ('focus',        'black',      'dark green'),
        ('dialog',       'black',      'light gray'),
        ('list_title',   'black',      'light gray',),
        ('error',        'white',      'dark red'),
    ]

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
                return yaml.load(f.read().strip())
        raise ConfigException('Unable to load environments file. Is '
                              'juju bootstrapped?')

    @property
    def password(self):
        PASSWORD_FILE = os.path.join(self.cfg_path, 'openstack.passwd')
        try:
            with open(PASSWORD_FILE) as f:
                _password = f.read().strip()
        except IOError:
            _password = 'password'
        return _password
