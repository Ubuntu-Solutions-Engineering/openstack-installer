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

configMaasEnvironment()
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

configLocalEnvironment()
{
	cat <<-EOF
		default: local

		environments:
		  local:
		    type: local
		    container: kvm
		EOF
}

configureJuju()
{
	env_type=$1
	shift

	mkdir -m 0700 "/home/$INSTALL_USER/.juju"
	$env_type $@ > "/home/$INSTALL_USER/.juju/environments.yaml"
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

	(cd "/home/$INSTALL_USER"; sudo -H -u "$INSTALL_USER" juju --show-log sync-tools)
	(cd "/home/$INSTALL_USER"; sudo -H -u "$INSTALL_USER" juju bootstrap --upload-tools) &
	waitForNodeStatus $system_id 6
	rm -rf /var/lib/lxc/juju-bootstrap/rootfs/var/lib/cloud/seed/*
	cp $TMP/maas.creds \
	    /var/lib/lxc/juju-bootstrap/rootfs/etc/cloud/cloud.cfg.d/91_maas.cfg
	lxc-start -n juju-bootstrap -d
	wait $!
}
