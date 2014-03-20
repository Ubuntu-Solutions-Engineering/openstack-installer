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
	wait-for-landscape

	# TODO: create a landscape user, get the user's credentials and make the
	# "RegisterMAASRegionController" API call. There is some discussion with
	# landscape-crew pending about how to do this.
}
