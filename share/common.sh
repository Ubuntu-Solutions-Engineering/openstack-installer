#
# common.sh - helper functions for cloud-install
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This package is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

. /usr/share/debconf/confmodule
db_version 2.0

BACKTITLE="Cloud install"
TMP=$(mktemp -d /tmp/cloud-install.XXX)

confValue()
{
    db_get $1 $2
    if [ -z "$RET" ]; then
	debconf-get-selections --installer | awk -F "\t" -v "owner=$1" \
	    -v "name=$2" '($1 == owner) && ($2 == name) { print $4 }'
    fi
}

getInstallUser()
{
    db_get cloud-install/install-user
    if [ -z "$RET" ]; then
	$(confValue user-setup-udeb passwd/username)
    else
	echo "$RET"
    fi
}

configIptablesNat()
{
	cat <<-EOF
		*nat
		:PREROUTING ACCEPT [0:0]
		:INPUT ACCEPT [0:0]
		:OUTPUT ACCEPT [0:0]
		:POSTROUTING ACCEPT [0:0]
		-A POSTROUTING -s $1 ! -d $1 -j MASQUERADE
		COMMIT
		EOF
}

configureNat()
{
	iptables -t nat -A POSTROUTING -s $1 ! -d $1 -j MASQUERADE
	configIptablesNat $1 > /etc/network/iptables.rules
	chmod 0600 /etc/network/iptables.rules
	sed -e '/^iface lo inet loopback$/a\
\	pre-up iptables-restore < /etc/network/iptables.rules' -i \
	    /etc/network/interfaces
}

disableBlank()
{
	tty=$(tty)
	if [ -n "$tty" ] && [ "${tty%%[0-9]}" = /dev/tty ]; then
		CONSOLE_BLANK=$(cat /sys/module/kernel/parameters/consoleblank)
		setterm -blank 0
	fi
}

enableBlank()
{
	if [ -n "$CONSOLE_BLANK" ]; then
		setterm -blank $((CONSOLE_BLANK/60))
	fi
}

enableIpForwarding()
{
	sed -e 's/^#net.ipv4.ip_forward=1$/net.ipv4.ip_forward=1/' -i \
	    /etc/sysctl.conf
	sysctl -p
}

error()
{
#    while true; do
	# whiptail --title "[!] An error has occurred" \
	#     --backtitle "$BACKTITLE" --ok-button Continue \
	#     --msgbox "Installation aborted\n\nSee /var/log/cloud-install.log for details.\nUse Alt+F2 to access console." \
	#     10 60
#    done
    echo "*** Error has occurred, see /var/log/cloud-install.log for details."
}

exitInstall()
{
	ret=$?
	wait
	if [ $ret -gt 0 ]; then
		error
	fi
	enableBlank
	rm -rf $TMP
}

gaugePrompt()
{
	printf "%s\n%s\n%s\n%s\n" XXX $1 "$2" XXX
}

generateSshKeys()
{
    if [ ! -e "/home/$INSTALL_USER/.ssh/id_rsa" ]; then
	sudo -u "$INSTALL_USER" ssh-keygen -N "" \
	    -f "/home/$INSTALL_USER/.ssh/id_rsa" 1>&2
    else
	echo "*** ssh keys exist for this user, they will be used instead."
	echo "*** If the current ssh keys are not passwordless you'll be"
	echo "*** required to enter your ssh key password during juju"
	echo "*** deployments."
    fi
}

waitForService()
{
	for service; do
		start wait-for-state WAITER=cloud-install \
		    WAIT_FOR=$service WAIT_STATE=running > /dev/null
	done
}

INSTALL_USER=$(getInstallUser)
