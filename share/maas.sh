#
# maas.sh - Shell routines related to MAAS
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This package is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

configBindOptions()
{
	cat <<"EOF"
options {
	directory "/var/cache/bind";

	forwarders {
EOF
	for forwarder; do
		printf "\t\t%s;\n" $forwarder
	done
	cat <<"EOF"
	};

	auth-nxdomain no;
	listen-on-v6 { any; };
};
EOF
}

configMaasBridge()
{
	cat <<"EOF"

auto br0
iface br0 inet static
	address 10.0.4.1
	netmask 255.255.255.0
	network 10.0.4.0
	broadcast 10.0.4.255
	bridge_ports none
EOF
}

configureDns()
{
	configBindOptions $(awk '/^nameserver / { print $2 }' /etc/resolv.conf) \
	    > /etc/bind/named.conf.options
	service bind9 restart
	sed -e '/^iface lo inet loopback$/a\
\	dns-nameservers 127.0.0.1' -i /etc/network/interfaces
	# lp 1102507
	ifdown lo; ifup lo
}

configureMaasImages()
{
	cp /usr/share/cloud-install-common/maas-data/* /etc/maas
	chmod 0640 /etc/maas/pserv.yaml
	chown :maas /etc/maas/pserv.yaml
}

configureMaasNetworking()
{
	address=$(ifconfig $2 | egrep -o "inet addr:[0-9.]+" \
	    | sed -e "s/^inet addr://")
	netmask=$(ifconfig $2 | egrep -o "Mask:[0-9.]+" \
	    | sed -e "s/^Mask://")
	broadcast=$(ifconfig $2 | egrep -o "Bcast:[0-9.]+" \
	    | sed -e "s/^Bcast://")
	if maasInterfaceExists $1 $2; then
		maas-cli maas node-group-interface update $1 $2 ip=$address \
		    interface=$2 management=2 subnet_mask=$netmask \
		    broadcast_ip=$broadcast router_ip=$3 ip_range_low=$4 \
		    ip_range_high=$5 1>&2
	else
		maas-cli maas node-group-interfaces new $1 ip=$address \
		    interface=$2 management=2 subnet_mask=$netmask \
		    broadcast_ip=$broadcast router_ip=$3 ip_range_low=$4 \
		    ip_range_high=$5 1>&2
	fi
}

createMaasBridge()
{
	configMaasBridge >> /etc/network/interfaces
	ifup br0 1>&2
}

createMaasSuperUser()
{
	password=$(cat /etc/openstack.passwd)
	printf "%s\n%s\n" "$password" "$password" \
	    | setsid sh -c "maas createsuperuser --username root --email root@example.com 1>&2"
}

maasAddress()
{
	echo $1 | tr . -
}

maasFilePath()
{
	maas-cli maas files list "prefix=$1" \
	    | python3 -c 'import json; import sys; print(json.load(sys.stdin)[0]["anon_resource_uri"])'
}

maasInterfaceExists()
{
	exists=$(maas-cli maas node-group-interfaces list $1 \
	    | python3 -c "import json; import sys; print(len([interface for interface in json.load(sys.stdin) if interface[\"interface\"] == \"$2\"]))")
	if [ $exists = 1 ]; then
		return 0
	else
		return 1
	fi
}

maasLogin()
{
	maas-cli login maas http://localhost/MAAS/api/1.0 $1
}

maasLogout()
{
	maas-cli logout maas
}

nodeSystemId()
{
	maas-cli maas nodes list mac_address=$1 \
	    | python3 -c 'import json; import sys; print json.load(sys.stdin)[0]["system_id"]'
}

waitForClusterRegistration()
{
	while true; do
		uuid=$(maas-cli maas node-groups list \
		    | python3 -c 'import json; import sys; print(json.load(sys.stdin)[0]["uuid"])')
		if [ $uuid != master ]; then
			break
		fi
		sleep 5
	done
}
