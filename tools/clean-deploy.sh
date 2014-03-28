#!/bin/bash

yes | juju destroy-environment

rm -r ~/.maascli.db
rm -rf ~/.juju ~/.cloud-install

sudo apt-get -yy purge '.*maas.*' '.*juju.*'

# these may or may not be installed, so we list them all individually
sudo apt-get -yy purge cloud-install-single
sudo apt-get -yy purge cloud-install-multi
sudo apt-get -yy purge cloud-install-landscape
sudo apt-get -yy purge cloud-installer

sudo lxc-stop -n juju-bootstrap
sudo lxc-destroy -n juju-bootstrap
sudo service apache2 stop
sudo rm /etc/.cloud-installed

# clean up the networking
sudo rm /etc/network/interfaces.d/cloud-install.cfg
sudo sed -i -e '/source/d' /etc/network/interfaces
sudo ifconfig br0 down
sudo brctl delbr br0
sudo service networking restart

echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
echo you might need to fix your /etc/resolv.conf
echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
