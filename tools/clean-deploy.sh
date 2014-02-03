#!/bin/bash

rm -rf ~/.juju

sudo apt-get -yy purge '.*maas.*' '.*juju.*'
sudo lxc-kill -n juju-bootstrap
sudo lxc-destroy -n juju-bootstrap
sudo service apache2 stop

echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
echo you might need to fix your /etc/resolv.conf
echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
