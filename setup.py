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

"""
cloud-installer
===============

Ubuntu Openstack installer is a metal to cloud image that provides an extremely
simple way to install, deploy and scale an openstack cloud on top of
Ubuntu server. Initial configurations are available for single
physical system deployments as well as multiple physical system
deployments.

Documentation
-------------
`Located at ReadTheDocs<http://ubuntu-cloud-installer.rtfd.org>`_
"""

from setuptools import setup, find_packages

import os
import sys

import cloudinstall

REQUIREMENTS = [
    "urwid",
    "PyYAML",
    "six",
    "requests",
    "requests_oauthlib"
]

TEST_REQUIREMENTS = list(REQUIREMENTS)
TEST_REQUIREMENTS.extend(["mock", "nose"])

if sys.argv[-1] == 'clean':
    print("Cleaning up ...")
    os.system('rm -rf cloud_installer.egg-info build dist')
    sys.exit()

setup(name='cloud-installer',
      version=cloudinstall.__version__,
      description="Openstack private cloud with Ubuntu Openstack installer",
      long_description=__doc__,
      author='Canonical Solutions Engineering',
      author_email='ubuntu-dev@lists.ubuntu.com',
      url='https://github.com/Ubuntu-Solutions-Engineering/cloud-installer',
      license="AGPLv3+",
      scripts=['bin/cloud-install', 'bin/cloud-status'],
      packages=find_packages(exclude=["test"]),
      data_files=[
          ('share/man/man1', ['man/en/cloud-status.1',
                              'man/en/cloud-install.1'])
          ],
     )
