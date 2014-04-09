#!/bin/bash

yes | juju destroy-environment --force local

rm -rf ~/.juju ~/.cloud-install
sudo rm /etc/.cloud-installed

sudo apt-get -yy purge '.*juju.*'

# these may or may not be installed, so we list them all individually
sudo apt-get -yy purge cloud-install-single
sudo apt-get -yy purge cloud-install-multi
sudo apt-get -yy purge cloud-install-landscape
sudo apt-get -yy purge cloud-installer

echo "@@@ Single install cleaned, re-run the installation steps."
