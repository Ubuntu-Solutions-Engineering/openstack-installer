#
# single.sh - Single install interface
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

singleInstall()
{
	whiptail --backtitle "$BACKTITLE" --infobox \
	    "Waiting for services to start" 8 60
	waitForService libvirt-bin lxc lxc-net

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

		gaugePrompt 20 "Configuring DNS"
		configureManualDns

		admin_secret=$(pwgen -s 32)
		storage_auth_key=$(pwgen -s 32)
		configureManualProvider $admin_secret $storage_auth_key
		gaugePrompt 80 "Bootstrapping Juju"
		bootstrapManualProvider
		echo 99

		gaugePrompt 100 "Installation complete"
		sleep 2
	} > $TMP/fifo
	wait $!
}
