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

apt_purge() {
  DEBIAN_FRONTEND=noninteractive apt-get -yy purge $@
}

case $WHAT in
  multi-system)
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    echo Multi install cleansing.
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    juju destroy-environment --yes --force maas
    rm -r ~/.maascli.db

    apt_purge '.*maas.*' 'bind9'
    sudo -u postgres psql -c 'drop database maasdb;'

    lxc-stop -n juju-bootstrap
    lxc-destroy -n juju-bootstrap

    # start lxcbr0 again
    sed -e 's/^USE_LXC_BRIDGE="false"/USE_LXC_BRIDGE="true"/' -i \
      /etc/default/lxc-net
    service lxc-net start

    # clean up the networking
    cp /etc/network/interfaces.cloud.bak /etc/network/interfaces
    rm /etc/network/interfaces.d/cloud-install.cfg
    ifconfig br0 down
    brctl delbr br0
    service networking restart

    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    echo you might need to fix your /etc/resolv.conf
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    ;;
  single-system)
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    echo Single install cleansing.
    echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    juju destroy-environment --yes --force local
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
apt_purge '.*juju.*'
apt_purge cloud-install-single
apt_purge cloud-install-multi
apt_purge cloud-install-landscape
apt_purge cloud-installer

# Remove any extra packages that aren't needed after purging.
apt-get -yy autoremove

# just make sure juju-mongodb died. LP#1306315
MONGOD=$(pgrep mongod)
RET=$?
if [ ${RET} -eq 0 ]; then
  if [ ${MONGOD} -gt 0 ]; then
    kill -9 ${MONGOD}
  fi
fi

rm -rf ~/.juju ~/.cloud-install || true
rm /etc/.cloud-installed || true
