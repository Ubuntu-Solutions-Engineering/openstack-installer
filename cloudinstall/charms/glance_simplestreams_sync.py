#
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

import glob
import logging
import os
import platform
import requests
import shutil
import subprocess

from cloudinstall.charms import (CharmBase, DisplayPriorities,
                                 CHARM_CONFIG,
                                 CHARM_CONFIG_FILENAME)

CHARM_STABLE_URL = ("https://api.github.com/repos/Ubuntu-Solutions-Engineering"
                    "/glance-simplestreams-sync-charm/tarball/stable")

# Not necessarily required to match because we're local, but easy enough to get
CURRENT_DISTRO = platform.linux_distribution()[-1]
CHARMS_DIR = os.path.expanduser("~/.cloud-install/local-charms")

log = logging.getLogger(__name__)


class CharmGlanceSimplestreamsSync(CharmBase):
    """ Charm directives for glance-simplestreams-sync  """

    charm_name = 'glance-simplestreams-sync'
    display_name = 'Glance - Simplestreams Image Sync'
    display_priority = DisplayPriorities.Other
    related = ['keystone']

    def download_stable(self):
        if not os.path.exists(CHARMS_DIR):
            os.makedirs(CHARMS_DIR)

        r = requests.get(CHARM_STABLE_URL, verify=True)
        tarball_name = os.path.join(CHARMS_DIR, 'stable.tar.gz')
        with open(tarball_name, mode='wb') as tarball:
            tarball.write(r.content)

        try:
            subprocess.check_output(['tar', '-C', CHARMS_DIR, '-zxf',
                                     tarball_name], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            log.warning("error untarring: rc={} out={}".format(e.returncode,
                                                               e.output))
            raise e

        # filename includes commit hash at end:
        srcpat = os.path.join(CHARMS_DIR,
                              'Ubuntu-Solutions-Engineering-'
                              'glance-simplestreams-sync-charm-*')
        srcs = glob.glob(srcpat)
        if len(srcs) != 1:
            log.warning("error finding downloaded stable charm."
                        " got {}".format(srcs))
            raise Exception("Could not find downloaded stable charm.")

        src = srcs[0]
        dest = os.path.join(CHARMS_DIR, CURRENT_DISTRO,
                            'glance-simplestreams-sync')
        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.renames(src, dest)

    def setup(self):
        """Temporary override to get local copy of charm."""

        log.debug("downloading stable branch from github")
        try:
            self.download_stable()
            log.debug("done: downloaded to " + CHARMS_DIR)

            log.debug("adding rabbitmq-server to relations list")
        except:
            log.exception("problem downloading stable branch."
                          " Falling back to charm store version.")
            super(CharmGlanceSimplestreamsSync, self).setup()
            return

        kwds = dict(machine_id=self.machine_id,
                    repodir=CHARMS_DIR,
                    distro=CURRENT_DISTRO)

        cmd = ('juju deploy --repository={repodir}'
               ' local:{distro}/glance-simplestreams-sync'
               ' --to {machine_id}').format(**kwds)

        if self.charm_name in CHARM_CONFIG:
            cmd += ' --config ' + CHARM_CONFIG_FILENAME

        try:
            log.debug("Deploying {} from local: {}".format(self.charm_name,
                                                           cmd))
            cmd_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                                 shell=True)

            log.debug("Deploy output: " + cmd_output.decode('utf-8'))

        except subprocess.CalledProcessError as e:
            log.warning("Deploy error. rc={} out={}".format(e.returncode,
                                                            e.output))

    def set_relations(self):
        if os.path.exists(os.path.join(CHARMS_DIR, CURRENT_DISTRO,
                                       'glance-simplestreams-sync')):
            self.related.append('rabbitmq-server')
            log.debug("Added rabbitmq to relation list")

        return super(CharmGlanceSimplestreamsSync, self).set_relations()


__charm_class__ = CharmGlanceSimplestreamsSync
