#
# multi.sh - Multi-install interface
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

multiInstall()
{

	mkdir -m 0700 "/home/$INSTALL_USER/.cloud-install" || true

        touch /home/$INSTALL_USER/.cloud-install/multi
	echo "$openstack_password" > "/home/$INSTALL_USER/.cloud-install/openstack.passwd"
	chmod 0600 "/home/$INSTALL_USER/.cloud-install/openstack.passwd"
	chown -R "$INSTALL_USER:$INSTALL_USER" "/home/$INSTALL_USER/.cloud-install"

	mkfifo -m 0600 $TMP/fifo
	whiptail --title "Installing" --backtitle "$BACKTITLE" \
	    --gauge "Please wait" 8 60 0 < $TMP/fifo &
	gauge_pid=$!
	{
		gaugePrompt 2 "Installing packages"
		# Use MaaS version closer to Trusty release (MaaS 1.5)
		apt-add-repository -y ppa:maas-maintainers/experimental
		apt-get update
		DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' -f -q -y cloud-install-multi </dev/null
		# lp 1247886
		service squid-deb-proxy start || true
		service lxc-net stop || true
		sed -e 's/^USE_LXC_BRIDGE="true"/USE_LXC_BRIDGE="false"/' -i \
		    /etc/default/lxc-net

		gaugePrompt 4 "Generating SSH keys"
		generateSshKeys

		gaugePrompt 6 "Creating MAAS super user"
		createMaasSuperUser
		echo 8
		maas_creds=$(maas-region-admin apikey --username root)
		saveMaasCreds $maas_creds
		maasLogin $maas_creds
		gaugePrompt 10 "Waiting for MAAS cluster registration"
		waitForClusterRegistration

		createMaasBridge $interface
		gaugePrompt 15 "Configuring MAAS networking"

		if [ -n "$bridge_interface" ]; then
			gateway=$(ipAddress br0)
			configureNat $(ipNetwork br0)
			enableIpForwarding
		fi

		# Retrieve dhcp-range
		configureMaasNetworking $uuid br0 $gateway \
		    ${dhcp_range%-*} ${dhcp_range#*-}
		gaugePrompt 18 "Configuring DNS"
		configureDns
		gaugePrompt 20 "Importing MAAS boot images"
		configureMaasImages

		if [ -z "$CLOUD_INSTALL_DEBUG" ]; then
			http_proxy=$MAAS_IMAGES_PROXY HTTP_PROXY=$MAAS_IMAGES_PROXY \
			    maas-import-pxe-files 1>&2
		fi

		gaugePrompt 60 "Configuring Juju"
		address=$(ipAddress br0)
		admin_secret=$(pwgen -s 32)
		configureJuju configMaasEnvironment $address $maas_creds $admin_secret
		gaugePrompt 75 "Bootstrapping Juju"
		host=$(maasAddress $address).master
		jujuBootstrap
		echo 99
		maas maas tags new name=use-fastpath-installer definition="true()"
		maasLogout

		gaugePrompt 100 "Installation complete"
		sleep 2
	} > $TMP/fifo
	wait $gauge_pid
}

saveMaasCreds()
{
	echo $1 > "/home/$INSTALL_USER/.cloud-install/maas-creds"
	chmod 0600 "/home/$INSTALL_USER/.cloud-install/maas-creds"
	chown "$INSTALL_USER:$INSTALL_USER" \
	    "/home/$INSTALL_USER/.cloud-install/maas-creds"
}
