#!/usr/bin/env python3
# -*- mode: python; -*-
#
# setup.py - MAAS distutils setup
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

from setuptools import setup

import os
import sys

import cloudinstall

if sys.argv[-1] == 'clean':
    print("Cleaning up ...")
    os.system('rm -rf cloud_installer.egg-info build dist')
    sys.exit()

setup(name='cloud-installer',
      version=cloudinstall.__version__,
      description="""Ubuntu Cloud installer is a metal to cloud
      image that provides an extremely simple way to install, deploy
      and scale an openstack cloud on top of Ubuntu server. Initial
      configurations are available for single physical system
      deployments as well as multiple physical system deployments.
      """,
      author='Robert Ayres',
      author_email='robert.ayres@ubuntu.com',
      url='https://launchpad.net/cloud-installer',
      license="GPLv3+",
      scripts=['bin/cloud-install', 'bin/cloud-status',
               'bin/wait-for-landscape', 'bin/ip_range.py'],
      packages=['cloudinstall', 'cloudinstall.maas', 'cloudinstall.juju'],
      requires=['PyYAML',
                'six',
                'urwid',
                'requests_oauthlib',
                'requests']
     )
