#
# multi.sh - Multi-install interface
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

multiInstall()
{
	set -ex
	whiptail --backtitle "$BACKTITLE" --infobox \
	    "Waiting for services to start" 8 60
	waitForService maas-region-celery maas-cluster-celery maas-pserv \
	    maas-txlongpoll

	# lp 1247886
	service squid-deb-proxy start || true

	mkdir -m 0700 "/home/$INSTALL_USER/.cloud-install" || true
	cp /etc/openstack.passwd "/home/$INSTALL_USER/.cloud-install"
	chown -R "$INSTALL_USER:$INSTALL_USER" "/home/$INSTALL_USER/.cloud-install"

	mkfifo -m 0600 $TMP/fifo
	whiptail --title "Installing" --backtitle "$BACKTITLE" \
	    --gauge "Please wait" 8 60 0 < $TMP/fifo &
	{
		gaugePrompt 2 "Generating SSH keys"
		generateSshKeys

		gaugePrompt 6 "Creating MAAS super user"
		createMaasSuperUser
		echo 8
		maas_creds=$(maas-region-admin apikey --username root)
		saveMaasCreds $maas_creds
		maasLogin $maas_creds
		gaugePrompt 10 "Waiting for MAAS cluster registration"
		waitForClusterRegistration

		installInterface=$(getInstallInterface)
		createMaasBridge $installInterface
		gaugePrompt 15 "Configuring MAAS networking"

		bridgeInterface=$(getBridgeInterface)
		if [ "$bridgeInterface" = "None" ]; then
			gateway=$(route -n | awk 'index($4, "G") { print $2 }')
		else
			gateway=$(ifconfig br0 | egrep -o "inet addr:[0-9.]+" \
			    | sed -e "s/^inet addr://")
			configureNat $(ip addr show $bridgeInterface | awk '/^    inet / { print $2 }')
			enableIpForwarding
		fi

		# Retrieve dhcp-range
		dhcp_range=$(getDhcpRange)
		configureMaasNetworking $uuid br0 $gateway \
		    ${dhcp_range%-*} ${dhcp_range#*-}
		gaugePrompt 18 "Configuring DNS"
		configureDns
		gaugePrompt 20 "Importing MAAS boot images"
		configureMaasImages

		if [ -z "$CLOUD_INSTALL_DEBUG" ]; then
			maas-import-pxe-files 1>&2
		fi

		gaugePrompt 70 "Configuring Juju"
		address=$(ifconfig br0 | egrep -o "inet addr:[0-9.]+" \
		    | sed -e "s/^inet addr://")
		admin_secret=$(pwgen -s 32)
		configureJuju $address $maas_creds $admin_secret
		gaugePrompt 60 "Bootstrapping Juju"
		host=$(maasAddress $address).master
		jujuBootstrap $uuid
		gaugePrompt 75 "Bootstrapping Juju"
		juju status
		echo 99
		maas maas tags new name=use-fastpath-installer definition="true()"
		maasLogout

		gaugePrompt 100 "Installation complete"
		sleep 2
	} > $TMP/fifo
	wait $!
}

saveMaasCreds()
{
	echo $1 > "/home/$INSTALL_USER/.cloud-install/maas-creds"
	chmod 0600 "/home/$INSTALL_USER/.cloud-install/maas-creds"
	chown "$INSTALL_USER:$INSTALL_USER" \
	    "/home/$INSTALL_USER/.cloud-install/maas-creds"
}
