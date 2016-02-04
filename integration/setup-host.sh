#!/bin/bash -ex
# This sets up the runner host
sudo apt-add-repository -y ppa:cloud-installer/experimental
sudo apt-add-repository -y ppa:juju/stable
sudo apt-get update
sudo apt-get install -qyf build-essential python3-pytest git

cd "$WORKSPACE/openstack-installer"
make git-sync-requirements
make install-dependencies
sudo dpkg -i openstack-build-deps*deb
sudo apt-get install -qyf
make deb
sudo make install
