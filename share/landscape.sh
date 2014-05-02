#
# landscape.sh - Landscape-install interface
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

getDomain() {
	echo "$1" | grep -E "^[^@]+@[^@]+\.[^@]+$" | sed -E -e 's/[^@]+@([^@]+\.[^@]+)/\1/'
}

configureLandscape() {
	state=1
	email_domain=example.com
	while [ -n "$state" ] && [ "$state" != 4 ]; do
		next_state=$((state + 1))
		case $state in
		1)
			admin_email=$(dialogInput "Landscape login" "Please enter the login email you would like to use for Landscape." 10 60)
			result=$(getDomain "$admin_email")
			if [ -z "$result" ]; then
				popState; continue
			fi
			email_domain="$result"
			;;
		2)
			suggested_name="$(getent passwd $INSTALL_USER | cut -d ':' -f 5 | cut -d ',' -f 1)"
			admin_name=$(dialogInput "Landscape user's full name" "Please enter the full name of the admin user for Landscape." 10 60 "$suggested_name")
			if [ -z "$admin_name" ]; then
				popState; continue
			fi
			;;
		3)
			system_email=$(dialogInput "Landscape system email" "Please enter the email that landscape should use as the system email." 10 60 "landscape@$email_domain")
			result=$(getDomain "$system_email")
			if [ -z "$result" ]; then
				popState; continue
			fi
			;;
		esac
		pushState "$state"
		state=$next_state
	done
}

deployLandscape()
{
	end_percent=${1:-100}
	mkfifo -m 0600 "$TMP/deployer-out"

	# For now, we assume that the install user has the landscape charm with the
	# right licensing configs cloned into their home directory; we can fix this
	# later when the landscape charm deploys with a free license.
	cd "/home/$INSTALL_USER/landscape-charm/config" && \
	    sudo -H -u "$INSTALL_USER" \
	    juju-deployer -Wdv -c landscape-deployments.yaml landscape-dense-maas \
	    > "$TMP/deployer-out" 2>&1 &

	lines_seen=0
	while IFS=: read unused; do
		lines_seen=$(($lines_seen + 1))

		# There are 77 lines in the juju-deployer output :-)
		percent=$((($lines_seen * $end_percent) / 77))

		# If someone suddenly starts spewing more output, just go to $end_percent
		percent=$(($percent < $end_percent ? $percent : $end_percent))
		dialogGaugePrompt $percent "Deploying Landscape"
	done < "$TMP/deployer-out"
	wait $!
	rm -f "$TMP/deployer-out"
}

landscapeInstall()
{
	configureLandscape

	# The landscape install needs a fully working juju bootstrap environment,
	# just like the multi install with no status screen does.
	multiInstall cloud-install-landscape

	dialogGaugeStart "Deploying Landscape" "Please wait" 8 70 0
	{
		# work around LP 1288685
		sleep 10

		deployLandscape 95

		dialogGaugePrompt 96 "Configuring Landscape"
		landscape_ip=$($configure_landscape \
		    --admin-email="$admin_email" \
		    --admin-name="$admin_name" \
		    --system-email="$system_email" \
		    --maas-host="$(ipAddress br0)")

	} > "$TMP/gauge"
	dialogGaugeStop

	echo "Your Landscape installation is complete!"
	echo "Please go to http://$landscape_ip/account/standalone/openstack to"
	echo "continue with the installation of your OpenStack cloud."
}
