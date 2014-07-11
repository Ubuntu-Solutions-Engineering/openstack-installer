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

# Multi-system install
#
# multiInstall
#
multiInstall()
{
	cp /etc/network/interfaces /etc/cloud-installer/interfaces.cloud.bak
	cp -r /etc/network/interfaces.d /etc/cloud-installer/interfaces.cloud.d.bak
	echo $interface > /etc/cloud-installer/interface

	dialogGaugeStart Installing "Please wait" 8 70 0
	{
		dialogGaugePrompt 2 "Setting up install"
		setupMultiInstall
		testAndConfigureInterface

		dialogAptInstall 4 20 ${1:-cloud-install-multi}

		service lxc-net stop || true
		sed -e 's/^USE_LXC_BRIDGE="true"/USE_LXC_BRIDGE="false"/' -i \
		    /etc/default/lxc-net

		dialogGaugePrompt 26 "Generating SSH keys"
		generateSshKeys

		dialogGaugePrompt 28 "Creating MAAS super user"
		createMaasSuperUser
		echo 30
		maas_creds=$(maas-region-admin apikey --username root)
		saveMaasCreds $maas_creds
		maasLogin $maas_creds
		dialogGaugePrompt 32 "Waiting for MAAS cluster registration"
		waitForClusterRegistration

		createMaasBridge $interface
		dialogGaugePrompt 34 "Configuring MAAS networking"

		if [ "$bridge_interface" = true ]; then
			gateway=$(ipAddress br0)
			configureNat $(ipNetwork br0)
			enableIpForwarding
		fi

		# Retrieve dhcp-range
		configureMaasNetworking $uuid br0 $gateway \
		    ${dhcp_range%-*} ${dhcp_range#*-}
		dialogGaugePrompt 36 "Configuring DNS"
		configureDns
		dialogGaugePrompt 40 "Importing MAAS boot images"
		configureMaasImages

		if [ -n "$MAAS_HTTP_PROXY" ]; then
			maas maas maas set-config name=http_proxy value="$MAAS_HTTP_PROXY" > /dev/null
		fi

		if [ -z "$CLOUD_INSTALL_DEBUG" ]; then
			http_proxy=$MAAS_HTTP_PROXY HTTP_PROXY=$MAAS_HTTP_PROXY maas-import-pxe-files > /dev/null
			$maas_report_boot_images > /dev/null
		fi

		dialogGaugePrompt 60 "Configuring Juju"
		address=$(ipAddress br0)
		admin_secret=$(pwgen -s 32)
		configureJuju configMaasEnvironment $address $maas_creds $admin_secret
		dialogGaugePrompt 75 "Bootstrapping Juju"
		jujuBootstrap $uuid
		maas maas tags new name=use-fastpath-installer definition="true()"
		chown $INSTALL_USER:$INSTALL_USER $INSTALL_HOME/.maascli.db

		dialogGaugePrompt 100 "Installation complete"
	} > "$TMP/gauge"
	dialogGaugeStop
}

# Store MAAS credentials
#
# saveMaasCreds credentials
#
# See multiInstall
#
saveMaasCreds()
{
	echo $1 > "$INSTALL_HOME/.cloud-install/maas-creds"
	chmod 0600 "$INSTALL_HOME/.cloud-install/maas-creds"
	chown "$INSTALL_USER:$INSTALL_USER" \
	    "$INSTALL_HOME/.cloud-install/maas-creds"
}

# Setup multi install
#
# setupMultiInstall
#
# See multiInstall
#
setupMultiInstall()
{
	mkdir -m 0700 -p "$INSTALL_HOME/.cloud-install"
	touch "$INSTALL_HOME/.cloud-install/multi"
	echo "$openstack_password" \
	    > "$INSTALL_HOME/.cloud-install/openstack.passwd"
	chmod 0600 "$INSTALL_HOME/.cloud-install/openstack.passwd"
	chown -R "$INSTALL_USER:$INSTALL_USER" \
	    "$INSTALL_HOME/.cloud-install"
	configCharmOptions $openstack_password > \
          "$INSTALL_HOME/.cloud-install/charmconf.yaml"
}

# Configure interface
#
# testAndConfigureInterface
#
# See multiInstall
#
testAndConfigureInterface()
{
	if [ -z "$(ipAddress $interface)" ]; then
		ifdown $interface && ifup $interface
		if [ -z "$(ipAddress $interface)" ]; then
			echo "You selected $interface which could not be configured." 1>&2
			echo "Please ensure $interface gets an IP address and re-run the installer." 1>&2
			false
		fi
	fi
}
