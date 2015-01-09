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
import uuid
from cloudinstall import utils
import logging


log = logging.getLogger('cloudinstall.config')


# The values of these three install types are user-visible strings:
INSTALL_TYPE_SINGLE = ("Single", "Fully containerized OpenStack installation "
                       "on a single machine.")
INSTALL_TYPE_MULTI = ("Multi", "OpenStack installation utilizing MAAS.")
INSTALL_TYPE_LANDSCAPE = ("Landscape OpenStack Autopilot",
                          "Benefit from best practices in cloud building, "
                          "and get up and running within minutes, all from "
                          "an intuitive web UI.")


class ConfigException(Exception):
    pass


class Config:
    STYLES = [
        ('body', 'white', 'black'),
        ('header_menu', 'light gray', 'dark gray'),
        ('header_title', 'light gray,bold', 'dark magenta'),
        ('subheading', 'dark gray,bold', 'default'),
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
        ('button_primary', 'white', 'dark gray', 'default', 'white', '#d51'),
        ('button_primary focus', 'dark blue,bold', 'dark gray', 'default',
         'white', '#b30'),
        ('button_secondary', 'white', 'dark gray', 'default',
         '#aaa', 'dark gray'),
        ('button_secondary focus', 'dark blue,bold', 'dark gray', 'default',
         'white', 'dark gray')
    ]

    def __init__(self, cfg_file=None):
        if os.getenv("FAKE_API_DATA"):
            self._juju_env = {"bootstrap-config": {'name': "fake",
                                                   'maas-server': "FAKE"}}
        else:
            self._juju_env = None
        self.node_install_wait_interval = 0.2

        if cfg_file is None:
            self._config_file = os.path.join(self.cfg_path, 'config.yaml')
        else:
            self._config_file = cfg_file

    def init(self):
        """ Create a new config file
        """
        if not os.path.exists(self._config_file):
            try:
                utils.spew(self._config_file, 'identifier: {}'.format(
                    uuid.uuid1()))
            except Exception as e:
                raise ConfigException("Unable to write configuration "
                                      "file: {}".format(e))
        else:
            raise ConfigException("Attempted to overwrite "
                                  "existing configuration file.")
        self.load()

    def save(self):
        """ Saves configuration """
        try:
            utils.spew(self._config_file,
                       yaml.safe_dump(self._config, default_flow_style=False))
            self.load()
        except IOError:
            raise ConfigException("Unable to save configuration.")

    def load(self):
        """ Loads configuration or refreshes config dict if exists """
        if os.path.exists(self._config_file):
            self._config = yaml.load(utils.slurp(self._config_file))
        else:
            raise ConfigException("Unable to load configuration.")

    @property
    def install_types(self):
        """ Installer types
        """
        return [INSTALL_TYPE_LANDSCAPE,
                INSTALL_TYPE_MULTI,
                INSTALL_TYPE_SINGLE]

    @property
    def pidfile(self):
        return os.path.join(self.cfg_path, 'openstack.pid')

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

    def setopt(self, key, val):
        """ sets config option """
        try:
            self._config[key] = val
            self.save()
        except Exception as e:
            log.error("Failed to set {} in config: {}".format(key, e))

    def getopt(self, key):
        if self._config and key in self._config:
            return self._config[key]
        else:
            log.error("Could not find {} in config".format(key))
            return str()

    def set_install_type(self, install_type):
        """ Stores installer type """
        # Sets install type
        utils.spew(os.path.join(self.cfg_path, install_type),
                   'auto-generated')

    @property
    def juju_path(self):
        return os.path.join(self.cfg_path)

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
            env_path = os.path.join(self.juju_path, 'environments', env_file)
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
        if os.path.exists(self.juju_environments_path):
            with open(self.juju_environments_path) as f:
                _env_yaml_raw = f.read()
                env_yaml = yaml.load(_env_yaml_raw)
        else:
            raise ConfigException(
                "{} unavailable, is juju bootstrapped?".format(
                    self.juju_environments_path))
        if key in env_yaml['environments'][provider]:
            env_yaml['environments'][provider][key] = val
        with open(self.juju_environments_path, 'w') as f:
            _env_yaml_raw = yaml.safe_dump(env_yaml, default_flow_style=False)
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
            log.exception('exception loading openstack password')
            raise ConfigException('cannot load saved openstack password')
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
            log.exception('exception loading maas creds')
            raise ConfigException("cannot load saved maas creds")
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
            log.exception("exception loading lanscape creds")
            raise ConfigException("cannot load landscape creds")
        return _creds
