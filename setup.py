#!/usr/bin/env python

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
      author_email='rober.ayres@ubuntu.com',
      url='https://launchpad.net/cloud-installer',
      license="GPLv3+",
      scripts=['bin/cloud-install'],
      packages=['cloudinstall', 'cloudinstall.maas'],
      requires=['PyYAML', 'six']
     )
