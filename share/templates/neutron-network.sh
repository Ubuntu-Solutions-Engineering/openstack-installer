#!/bin/bash -e

if [[ "$1" == "Single" ]]; then
    [ ! -e /etc/network/interfaces.d/br-ex.cfg ] || { echo "Network configured already."; exit 0; }
    ifdown eth1
    ovs-vsctl add-port br-ex eth1
    mac=$(ifconfig eth1 | grep -E -o "HWaddr [a-z0-9:]+" | sed -e "s/^HWaddr //")
    ovs-vsctl set bridge br-ex other-config:hwaddr=$mac
    [ -f /etc/network/interfaces.d/eth1.cfg ] && { mv /etc/network/interfaces.d/eth1.cfg /etc/network/interfaces.d/eth1.cfg.bak; }
    cat <<EOF> /etc/network/interfaces.d/br-ex.cfg
auto eth1
iface eth1 inet manual

auto br-ex
iface br-ex inet dhcp
EOF
    ifup eth1 br-ex
fi
