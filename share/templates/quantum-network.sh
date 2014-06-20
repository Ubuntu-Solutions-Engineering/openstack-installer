#!/bin/sh -e

ifdown eth0
ovs-vsctl add-port br-ex eth0
mac=$(ifconfig eth0 | grep -E -o "HWaddr [a-z0-9:]+" | sed -e "s/^HWaddr //")
ovs-vsctl set bridge br-ex other-config:hwaddr=$mac
mv /etc/network/interfaces.d/eth0.cfg /etc/network/interfaces.d/eth0.cfg.bak
cat <<-"EOF" > /etc/network/interfaces.d/br-ex.cfg
	auto eth0
	iface eth0 inet manual

	auto br-ex
	iface br-ex inet dhcp
	EOF
ifup eth0 br-ex
