#
# juju.sh - Shell routines for Juju
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

configJujuEnvironment()
{
	cat <<-EOF
		default: maas

		environments:
		  maas:
		    type: maas
		    maas-server: 'http://$1/MAAS/'
		    maas-oauth: '$2'
		    admin-secret: $3
		    default-series: precise
		    authorized-keys-path: ~/.ssh/id_rsa.pub
		EOF
}

configManualEnvironment()
{
	cat <<-EOF
		default: "null"

		environments:
		  "null":
		    type: "null"
		    admin-secret: $1
		    bootstrap-host: juju-bootstrap
		    bootstrap-user: ubuntu
		    storage-auth-key: $2
		EOF
}

configureJuju()
{
	mkdir -m 0700 "/home/$INSTALL_USER/.juju"
	configJujuEnvironment $1 $2 $3 \
	    > "/home/$INSTALL_USER/.juju/environments.yaml"
	chmod 0600 "/home/$INSTALL_USER/.juju/environments.yaml"
	chown -R -- "$INSTALL_USER:$INSTALL_USER" "/home/$INSTALL_USER/.juju"
}

configureManualDns()
{
	cp /etc/resolv.conf /etc/resolv.dnsmasq
	echo resolv-file=/etc/resolv.dnsmasq > /etc/lxc/dnsmasq.conf
	echo LXC_DHCP_CONFILE=/etc/lxc/dnsmasq.conf >> /etc/default/lxc-net
	service lxc-net restart
	sed -e '/^iface lo inet loopback$/a\
\	dns-nameservers 10.0.3.1' -i /etc/network/interfaces
	# lp 1102507
	ifdown lo; ifup lo
}

configureManualProvider()
{
	mkdir -m 0700 -p "/home/$INSTALL_USER/.juju"
	configManualEnvironment $1 $2 \
	    > "/home/$INSTALL_USER/.juju/environments.yaml"
	chmod 0600 "/home/$INSTALL_USER/.juju/environments.yaml"
	chown -R -- "$INSTALL_USER:$INSTALL_USER" "/home/$INSTALL_USER/.juju"
}

# TODO break this function into smaller ones
jujuBootstrap()
{
	lxc-create -n juju-bootstrap -t ubuntu-cloud -- -r precise
	sed -e "s/^lxc.network.link.*$/lxc.network.link = br0/" -i \
	    /var/lib/lxc/juju-bootstrap/config

	mac=$(grep lxc.network.hwaddr /var/lib/lxc/juju-bootstrap/config \
	    | cut -d " " -f 3)
	# TODO dynamic architecture selection
	# NOTE: nodegroup= here intentionally left blank.
	maas maas nodes new architecture=amd64/generic mac_addresses=$mac \
	    hostname=juju-bootstrap nodegroup= power_type=virsh
	system_id=$(nodeSystemId $mac)
	wget -O $TMP/maas.creds \
	    "http://localhost/MAAS/metadata/latest/by-id/$system_id/?op=get_preseed"
	python2 /etc/maas/templates/commissioning-user-data/snippets/maas_signal.py \
	    --config $TMP/maas.creds OK || true

	(cd "/home/$INSTALL_USER"; sudo -H -u "$INSTALL_USER" juju bootstrap --upload-tools) &
	# TODO There is a delay between adding a machine via the cli, which
	#      returns instantly, and the juju provisioning worker picking up
	#      the request and creating the necessary machine placeholder.
	#      Ideally we'd keep polling the output of juju status before
	#      proceeding. For now we just sleep.
	sleep 20
	rm -rf /var/lib/lxc/juju-bootstrap/rootfs/var/lib/cloud/seed/*
	cp $TMP/maas.creds \
	    /var/lib/lxc/juju-bootstrap/rootfs/etc/cloud/cloud.cfg.d/91_maas.cfg
	lxc-start -n juju-bootstrap -d
	wait $!
}

bootstrapManualProvider()
{
	lxc-create -n juju-bootstrap -t ubuntu-cloud -- -r precise \
	    -S "/home/$INSTALL_USER/.ssh/id_rsa.pub"
	lxc-start -n juju-bootstrap -d
	# wait for container to boot
	sleep 20
	(
		cd "/home/$INSTALL_USER"
		# lp 1238934
		sudo -H -u "$INSTALL_USER" ssh -o StrictHostKeyChecking=no \
		    ubuntu@juju-bootstrap \
		    'sh -c "sudo add-apt-repository -y cloud-archive:tools && sudo apt-get update"'
		sudo -H -u "$INSTALL_USER" juju bootstrap --upload-tools
	)
}
