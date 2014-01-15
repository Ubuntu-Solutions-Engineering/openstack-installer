multiInstall()
{
	whiptail --backtitle "$BACKTITLE" --infobox \
	    "Waiting for services to start" 8 60
	waitForService maas-region-celery maas-cluster-celery maas-pserv \
	    maas-txlongpoll

	# lp 1247886
	service squid-deb-proxy start || true

	mkdir -m 0700 "/home/$INSTALL_USER/.cloud-install"
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
		maas_creds=$(cloud-install maas-creds root)
		saveMaasCreds $maas_creds
		maasLogin $maas_creds
		gaugePrompt 10 "Waiting for MAAS cluster registration"
		waitForClusterRegistration
		interface=$(ifquery -X lo --list)
		manage_dhcp=$(confValue cloud-install-udeb \
		    cloud-install/manage-dhcp)
		if [ $manage_dhcp = true ]; then
			gaugePrompt 15 "Configuring MAAS networking"
			gateway=$(route -n | awk 'index($4, "G") { print $2 }')
			dhcp_range=$(confValue cloud-install-udeb \
			    cloud-install/dhcp-range)
			configureMaasNetworking $uuid $interface $gateway \
			    ${dhcp_range%-*} ${dhcp_range#*-}
			gaugePrompt 18 "Configuring DNS"
			configureDns
		fi
		gaugePrompt 20 "Importing MAAS boot images"
		configureMaasImages
		maas-import-pxe-files 1>&2

		gaugePrompt 70 "Configuring Juju"
		address=$(ifconfig $interface | egrep -o "inet addr:[0-9.]+" \
		    | sed -e "s/^inet addr://")
		admin_secret=$(pwgen -s 32)
		configureJuju $address $maas_creds $admin_secret
		gaugePrompt 80 "Bootstrapping Juju"
		host=$(maasAddress $address).master
		jujuBootstrap $address $host $maas_creds $admin_secret
		echo 99
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
