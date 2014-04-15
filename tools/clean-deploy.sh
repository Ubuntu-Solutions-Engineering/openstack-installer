#!/bin/bash

if [ "$#" -eq 1 ]; then
  WHAT=$1
elif [ -f ~/.cloud-install/multi ]; then
  WHAT=multi-system
elif [ -f ~/.cloud-install/single ]; then
  WHAT=single-system
else
  echo "could not determine install type"
fi

case $WHAT in
  multi-system)
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    echo Multi install cleansing.
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    yes | juju destroy-environment --force maas
    rm -r ~/.maascli.db
    sudo apt-get -yy purge '.*maas.*' 'bind9'
    sudo lxc-stop -n juju-bootstrap
    sudo lxc-destroy -n juju-bootstrap
    sudo service apache2 stop
    # clean up the networking
    sudo rm /etc/network/interfaces.d/cloud-install.cfg
    sudo sed -i -e '/source/d' /etc/network/interfaces
    sudo ifconfig br0 down
    sudo brctl delbr br0
    sudo service networking restart

    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    echo you might need to fix your /etc/resolv.conf
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    ;;
  single-system)
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    echo Single install cleansing.
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    yes | juju destroy-environment --force local
    ;;
  *)
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    echo Please run with either single-system or multi-system as an argument.
    echo Example:
    echo   ./clean-deploy.sh single-system
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    exit 1
    ;;
  esac

# these may or may not be installed, so we list them all individually
sudo apt-get -yy purge '.*juju.*'
sudo apt-get -q -yy purge cloud-install-single
sudo apt-get -q -yy purge cloud-install-multi
sudo apt-get -q -yy purge cloud-install-landscape
sudo apt-get -q -yy purge cloud-installer

# just make sure juju-mongodb died. LP#1306315
MONGOD=$(pgrep mongod)
RET=$?
if [ ${RET} -eq 0 ]; then
  if [ ${MONGOD} -gt 0 ]; then
    sudo kill -9 ${MONGOD}
  fi
fi

sudo rm -rf ~/.juju ~/.cloud-install || true
sudo rm /etc/.cloud-installed || true

