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

# Deploy Landscape
#
# deployLandscape percent
#
deployLandscape()
{
	end_percent=${1:-100}
	mkfifo -m 0600 "$TMP/deployer-out"

	# Randomize landscape's internal databse password.
	sed -i -e "s/look-a-different-password/$(pwgen -s 32)/" \
		$TEMPLATES/landscape-deployments.yaml

	sudo -H -u "$INSTALL_USER" \
		juju-deployer -Wdv -c $TEMPLATES/landscape-deployments.yaml landscape-dense-maas \
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

# Landscape install
#
# landscapeInstall
#
landscapeInstall()
{
	# The landscape install needs a fully working juju bootstrap environment,
	# just like the multi install with no status screen does.
	multiInstall cloud-install-landscape

	dialogGaugeStart "Deploying Landscape" "Please wait" 8 70 0
	{
		# work around LP 1288685
		sleep 10

		deployLandscape 95

		dialogGaugePrompt 96 "Configuring Landscape"
		maas_ip=$(ipAddress br0)
		landscape_ip=$($configure_landscape \
		    --admin-email="$admin_email" \
		    --admin-name="$admin_name" \
		    --system-email="$system_email" \
		    --maas-host="$maas_ip")

	} > "$TMP/gauge"
	dialogGaugeStop

	echo "You can now accept enlisted nodes in MaaS by visiting"
	echo "http://$maas_ip/MAAS/. The username is root' and the password is the"
	echo "one you provided during the install process."
	echo "Please go to http://$landscape_ip/account/standalone/openstack to"
	echo "continue with the installation of your OpenStack cloud."
}
