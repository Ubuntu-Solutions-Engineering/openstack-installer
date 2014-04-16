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
	touch /home/$INSTALL_USER/.cloud-install/multi

	dialogGaugeStart Installing "Please wait" 8 70 0
	{
		dialogAptInstall 2 18 cloud-install-multi

		service lxc-net stop || true
		sed -e 's/^USE_LXC_BRIDGE="true"/USE_LXC_BRIDGE="false"/' -i \
		    /etc/default/lxc-net

		dialogGaugePrompt 22 "Generating SSH keys"
		generateSshKeys

		dialogGaugePrompt 24 "Creating MAAS super user"
		createMaasSuperUser
		echo 25
		maas_creds=$(maas-region-admin apikey --username root)
		saveMaasCreds $maas_creds
		maasLogin $maas_creds
		dialogGaugePrompt 26 "Waiting for MAAS cluster registration"
		waitForClusterRegistration

		createMaasBridge $interface
		dialogGaugePrompt 30 "Configuring MAAS networking"

		if [ -n "$bridge_interface" ]; then
			gateway=$(ipAddress br0)
			configureNat $(ipNetwork br0)
			enableIpForwarding
			configureMaasServices $gateway
		fi

		# Retrieve dhcp-range
		configureMaasNetworking $uuid br0 $gateway \
		    ${dhcp_range%-*} ${dhcp_range#*-}
		dialogGaugePrompt 35 "Configuring DNS"
		configureDns
		dialogGaugePrompt 40 "Importing MAAS boot images"
		configureMaasImages

		if [ -n "$MAAS_HTTP_PROXY" ]; then
			maas maas maas set-config name=http_proxy value="$MAAS_HTTP_PROXY"
		fi

		if [ -z "$CLOUD_INSTALL_DEBUG" ]; then
			http_proxy=$MAAS_HTTP_PROXY HTTP_PROXY=$MAAS_HTTP_PROXY maas-import-pxe-files
			$maas_report_boot_images
		fi

		dialogGaugePrompt 60 "Configuring Juju"
		address=$(ipAddress br0)
		admin_secret=$(pwgen -s 32)
		configureJuju configMaasEnvironment $address $maas_creds $admin_secret
		dialogGaugePrompt 75 "Bootstrapping Juju"
		jujuBootstrap $uuid
		echo 99
		maas maas tags new name=use-fastpath-installer definition="true()"
		maasLogout

		dialogGaugePrompt 100 "Installation complete"
		sleep 2
	} > "$TMP/gauge"
	dialogGaugeStop
}

saveMaasCreds()
{
	echo $1 > "/home/$INSTALL_USER/.cloud-install/maas-creds"
	chmod 0600 "/home/$INSTALL_USER/.cloud-install/maas-creds"
	chown "$INSTALL_USER:$INSTALL_USER" \
	    "/home/$INSTALL_USER/.cloud-install/maas-creds"
}
