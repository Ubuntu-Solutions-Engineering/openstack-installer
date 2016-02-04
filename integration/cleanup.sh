#!/bin/bash -ex

sudo openstack-install -u --force || true && sudo rm -rf ~/.cloud-install || true
sudo apt-get remove -y juju openstack lxd lxc || true
sudo apt-get autoremove -y
