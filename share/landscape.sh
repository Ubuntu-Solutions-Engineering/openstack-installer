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

getLandscapeCert() {
	begin="-----BEGIN CERTIFICATE-----"
	end="-----END CERTIFICATE-----"
	cert=$(echo | openssl s_client -connect "$1":443 < /dev/null 2>/dev/null)
	echo "$begin"
	echo "$cert" | sed '1,/^-----BEGIN CERTIFICATE-----$/d' \
	    | sed '/^-----END CERTIFICATE-----$/,$d'
	echo "$end"
}

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

getDictField() {
  python3 -c "d = $1; print(d['$2'])"
}

landscapeInstall()
{
	configureLandscape

	# The landscape install needs a fully working juju bootstrap environment,
	# just like the multi install with no status screen does.
	multiInstall cloud-install-landscape

	# work around LP 1288685
	sleep 10

	# For now, we assume that the install user has the landscape charm with the
	# right licensing configs cloned into their home directory; we can fix this
	# later when the landscape charm deploys with a free license.
	cd "/home/$INSTALL_USER/landscape-charm/config" && \
	    sudo -H -u "$INSTALL_USER" \
	    juju-deployer -Wdv -c landscape-deployments.yaml landscape-dense-maas

	# Landscape isn't actually up when juju-deployer exits; the relations take a
	# while to set up and deployer doesn't wait until they're finished (it has
	# no way to, viz. LP #1254766), so we wait until everything is ok.
	landscape_ip=$($wait_for_landscape)

	certfile=~/.cloud-install/landscape-ca.pem
	getLandscapeCert "$landscape_ip" > "$certfile"

	# landscape-api just prints a __repr__ of the response we get, which contains
	# both LANDSCAPE_API_KEY and LANDSCAPE_API_SECRET for the user.
	resp=$(landscape-api \
	    --key anonymous --secret anonymous --uri "https://$landscape_ip/api/" \
	    --ssl-ca-file "$certfile" \
	    call BootstrapLDS \
	    admin_email="$admin_email" \
	    admin_password=$(cat "/home/$INSTALL_USER/.cloud-install/openstack.passwd") \
	    admin_name="$admin_name"
	    root_url="https://$landscape_ip/" \
	    system_email="$system_email")
	landscape_api_key=$(getDictField "$resp" LANDSCAPE_API_KEY)
	landscape_api_secret=$(getDictField "$resp" LANDSCAPE_API_SECRET)

	landscape-api \
	    --key "$landscape_api_key" \
	    --secret "$landscape_api_secret" \
	    --uri "https://$landscape_ip/api/" \
	    --ssl-ca-file "$certfile" \
	    register-maas-region-controller \
	    endpoint="http://$(ipAddress br0)/MAAS" \
	    credentials="$(cat /home/$INSTALL_USER/.cloud-install/maas-creds)"

	echo "Your Landscape installation is complete!"
	echo "Please go to http://$landscape_ip/account/standalone/openstack to"
	echo "continue with the installation of your OpenStack cloud."
}
