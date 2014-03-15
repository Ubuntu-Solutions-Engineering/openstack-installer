#
# maas.sh - Shell routines related to MAAS
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
	cat <<-EOF
		auto $1
		iface $1 inet manual

		auto br0
		EOF
	cat "$2"
	printf "\t%s\n" "bridge_ports $1"
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
	cp /usr/share/cloud-installer/maas-data/* /etc/maas
	chmod 0640 /etc/maas/pserv.yaml
	chown :maas /etc/maas/pserv.yaml
}

configureMaasInterfaces()
{
	awk -v interface=$1 -v "bridge_cfg=$2" -f - "$3" <<-"EOF"
		function strip(s)
		{
		    sub(/^[[:blank:]]+/, "", s)
		    sub(/[[:blank:]]+$/, "", s)
		    return s
		}

		/^[[:blank:]]*(iface|mapping|auto|allow-[^ ]+|source) / {
		    s_iface = 0; iface = 0
		}

		$0 ~ "^[[:blank:]]*auto (" interface "|br0)[[:blank:]]*$" { print "#" $0; next }

		$0 ~ "^[[:blank:]]*iface (" interface "|br0) " {
		    s_iface = 1
		    if ($2 == interface) {
		        iface = 1
		        print "iface br0", $3, $4 > bridge_cfg
		    }
		    print "#" $0
		    next
		}

		s_iface == 1 {
		    if (iface == 1) {
		        print "\t" strip($0) > bridge_cfg
		    }
		    print "#" $0
		    next
		}

		{ print $0 }
		EOF
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
		maas maas node-group-interface update $1 $2 ip=$address \
		    interface=$2 management=2 subnet_mask=$netmask \
		    broadcast_ip=$broadcast router_ip=$3 ip_range_low=$4 \
		    ip_range_high=$5 1>&2
	else
		maas maas node-group-interfaces new $1 ip=$address \
		    interface=$2 management=2 subnet_mask=$netmask \
		    broadcast_ip=$broadcast router_ip=$3 ip_range_low=$4 \
		    ip_range_high=$5 1>&2
	fi
}

createMaasBridge()
{
	ifdown $1 br0 1>&2 || true
	for cfg in /etc/network/interfaces /etc/network/interfaces.d/*.cfg; do
		[ -e "$cfg" ] || continue
		configureMaasInterfaces $1 $TMP/bridge.cfg "$cfg" \
		    > $TMP/interfaces.cfg
		mv $TMP/interfaces.cfg "$cfg"
	done
	if ! grep -Eq '^[[:blank:]]*source /etc/network/interfaces\.d/\*\.cfg[[:blank:]]*$' \
	    /etc/network/interfaces; then
		printf "\n%s\n" "source /etc/network/interfaces.d/*.cfg" \
		    >> /etc/network/interfaces
	fi
	mkdir -p /etc/network/interfaces.d
	configMaasBridge $1 $TMP/bridge.cfg \
	    > /etc/network/interfaces.d/cloud-install.cfg
	ifup $1 br0 1>&2
}

createMaasSuperUser()
{
	password=$(cat "/home/$INSTALL_USER/.cloud-install/openstack.passwd")
	printf "%s\n%s\n" "$password" "$password" \
	    | setsid sh -c "maas-region-admin createsuperuser --username root --email root@example.com 1>&2"
}

maasAddress()
{
	echo $1 | tr . -
}

maasFilePath()
{
	maas maas files list "prefix=$1" \
	    | python3 -c 'import json; import sys; print(json.load(sys.stdin)[0]["anon_resource_uri"])'
}

maasInterfaceExists()
{
	exists=$(maas maas node-group-interfaces list $1 \
	    | python3 -c "import json; import sys; print(len([interface for interface in json.load(sys.stdin) if interface[\"interface\"] == \"$2\"]))")
	if [ $exists = 1 ]; then
		return 0
	else
		return 1
	fi
}

maasLogin()
{
	maas login maas http://localhost/MAAS/api/1.0 $1
}

maasLogout()
{
	maas logout maas
	rm -rf /home/$INSTALL_USER/.maascli.db
}

nodeStatus()
{
	maas maas nodes list id=$1 \
	    | python3 -c 'import json; import sys; print(json.load(sys.stdin)[0]["status"])'
}

nodeSystemId()
{
	maas maas nodes list mac_address=$1 \
	    | python3 -c 'import json; import sys; print(json.load(sys.stdin)[0]["system_id"])'
}

waitForClusterRegistration()
{
	while true; do
		uuid=$(maas maas node-groups list \
		    | python3 -c 'import json; import sys; print(json.load(sys.stdin)[0]["uuid"])')
		if [ $uuid != master ]; then
			break
		fi
		sleep 5
	done
}

waitForNodeStatus()
{
	while [ $(nodeStatus $1) -ne $2 ]; do
		sleep 5
	done
}
