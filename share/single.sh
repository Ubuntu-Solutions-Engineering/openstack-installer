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

	mkdir -m 0700 "/home/$INSTALL_USER/.cloud-install" || true

        touch /home/$INSTALL_USER/.cloud-install/single
	echo "$openstack_password" > "/home/$INSTALL_USER/.cloud-install/openstack.passwd"
	chmod 0600 "/home/$INSTALL_USER/.cloud-install/openstack.passwd"
	chown -R "$INSTALL_USER:$INSTALL_USER" "/home/$INSTALL_USER/.cloud-install"

	mkfifo -m 0600 $TMP/fifo
	whiptail --title "Installing" --backtitle "$BACKTITLE" \
	    --gauge "Please wait" 8 60 0 < $TMP/fifo &
	{
		gaugePrompt 2 "Installing packages"
		apt-get -y install cloud-install-single

		gaugePrompt 4 "Generating SSH keys"
		generateSshKeys

		gaugePrompt 80 "Bootstrapping Juju"
		configureJuju configLocalEnvironment
                (
                  cd "/home/$INSTALL_USER"
                  sudo -H -u "$INSTALL_USER" juju bootstrap
                  sudo -H -u "$INSTALL_USER" juju set-constraints mem=1G
                )
		echo 99

		gaugePrompt 100 "Installation complete"
		sleep 2
	} > $TMP/fifo
	wait $!
}
