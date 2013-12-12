singleInstall()
{
	whiptail --backtitle "$BACKTITLE" --infobox \
	    "Waiting for services to start" 8 60
	waitForService maas-region-celery maas-cluster-celery maas-pserv \
	    maas-txlongpoll

	# lp 1247886
	service squid-deb-proxy start || true

	mkdir -m 0700 "/home/$INSTALL_USER/.cloud-install"
	touch "/home/$INSTALL_USER/.cloud-install/single"
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
		maas_creds=$(maas-get-user-creds root)
		saveMaasCreds $maas_creds
		maasLogin $maas_creds
		gaugePrompt 10 "Waiting for MAAS cluster registration"
		waitForClusterRegistration
		gaugePrompt 12 "Creating MAAS bridge"
		createMaasBridge
		gaugePrompt 15 "Configuring MAAS networking"
		configureMaasNetworking $uuid br0 10.0.4.1 10.0.4.100 10.0.4.199
		gaugePrompt 18 "Configuring DNS"
		configureDns

    gaugePrompt 40 "Downloading images"
    uvtInstall

    gaugePrompt 69 "LSB release hack"
    lsbReleaseHack

		gaugePrompt 70 "Configuring Juju"
		admin_secret=$(pwgen -s 32)
		configureJuju 10.0.4.1 $maas_creds $admin_secret
		gaugePrompt 80 "Bootstrapping Juju"
		host=$(maasAddress 10.0.4.1).master
		jujuBootstrap 10.0.4.1 $host $maas_creds $admin_secret
		gaugePrompt 85 "Deploying host machine"
		deployHostMachine $host $admin_secret
		gaugePrompt 90 "Configuring network forwarding"
		enableIpForwarding
		configureNat 10.0.4.0/24
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

uvtInstall()
{
  # uvtool needs to be installed while libvirtd is running.
  apt-get -y install uvtool

  system_arch=$(dpkg --print-architecture)
  uvt-simplestreams-libvirt sync arch=$system_arch release=precise
}

# XXX: HACK: TODO: Juju looks at the environment (i.e. /etc/lsb-release) to
# figure out what kind of container to deploy. The charms require precise
# containers, so we fake a precise environment.
lsbReleaseHack()
{
  sed -i -e 's/13.10/12.04/g' -e 's/saucy/precise/' /etc/lsb-release
}
