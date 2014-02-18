#!/bin/bash

juju destroy-environment

rm -rf ~/.juju

sudo apt-get -yy purge '.*maas.*' '.*juju.*'
sudo lxc-stop -n juju-bootstrap
sudo lxc-destroy -n juju-bootstrap
sudo service apache2 stop
sudo rm /etc/.cloud-installed

echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
echo you might need to fix your /etc/resolv.conf
echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
