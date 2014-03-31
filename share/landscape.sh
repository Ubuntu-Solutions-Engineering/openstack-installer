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

function getLandscapeCert() {
	begin="-----BEGIN CERTIFICATE-----"
	end="-----END CERTIFICATE-----"
	cert=$(echo | openssl s_client -connect "$1":443 < /dev/null 2>/dev/null)
	echo "$begin"
	echo "$cert" | sed '1,/^-----BEGIN CERTIFICATE-----$/d' \
	    | sed '/^-----END CERTIFICATE-----$/,$d'
	echo "$end"
}

landscapeInstall()
{
	# The landscape install needs a fully working juju bootstrap environment,
	# just like the multi install with no status screen does.
	multiInstall

	# For now, we assume that the install user has the landscape charm with the
	# right licensing configs cloned into their home directory; we can fix this
	# later when the landscape charm deploys with a free license.
	cd "/home/$INSTALL_USER/landscape-charm/config" && \
      juju-deployer -Wdv -c landscape-deployments.yaml landscape-dense-maas

	# Landscape isn't actually up when juju-deployer exits; the relations take a
	# while to set up and deployer doesn't wait until they're finished (it has
	# no way to, viz. LP #1254766), so we wait until everything is ok.
	landscape_ip=$(wait-for-landscape)

	certfile=~/.cloud-install/landscape-ca.pem
	get_certificate "http://$landscape_ip/api/" > "$certfile"

	# TODO: should we ask about these emails and things?
	landscape-api \
	    --key anonymous --secret anonymous --uri "https://$landscape_ip/api/" \
	    --ssl-ca-file "$certfile" \
	    call BootstrapLDS \
	    admin_email='foo@example.com' \
	    admin_password=$(cat "/home/$INSTALL_USER/.cloud-install/openstack.passwd") \
	    admin_name='Steve Irwin' \
	    root_url="https://$landscape_ip/" \
	    system_email='landscape@example.com'

	echo "Your Landscape installation is complete!"
	echo "Please go to http://$landscape_ip/account/standalone/openstack to"
	echo "continue with the installation of your OpenStack cloud."
}
