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
	touch /home/$INSTALL_USER/.cloud-install/single

	memory=$(head -n 1 /proc/meminfo | awk '/[0-9]/ {print $2}')

	# we require 8gb for the single install
	if [ "$memory" -lt $((8 * 1024 * 1024)) ] && [ -z "$force_install" ]; then
		dialogMsgBox "Insufficient Memory!" "Abort" \
		    "You need at least 8GB of memory to run the single machine install." 10 60

		# Clean up after ourselves since we failed.
		rm -rf /home/$INSTALL_USER/.cloud-install
		return 0
	fi

	dialogGaugeStart Installing "Please wait" 8 70 0
	{
		dialogAptInstall 2 18 cloud-install-single

		dialogGaugePrompt 22 "Generating SSH keys"
		generateSshKeys

		dialogGaugePrompt 80 "Bootstrapping Juju"
		configureJuju configLocalEnvironment
                (
                  cd "/home/$INSTALL_USER"
                  sudo -H -u "$INSTALL_USER" juju bootstrap
                  sudo -H -u "$INSTALL_USER" juju set-constraints mem=1G
                )
		echo 99

		dialogGaugePrompt 100 "Installation complete"
		sleep 2
	} > "$TMP/gauge"
	dialogGaugeStop
}
