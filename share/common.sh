#
# common.sh - helper functions for cloud-install
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

BACKTITLE="Cloud install"
LOG=/var/log/cloud-install.log

export PYTHONPATH=/usr/share/cloud-installer:$PYTHONPATH
export PYTHONDONTWRITEBYTECODE=true

# Absolute path
#
# absolutePath path
#
# writes absolute path to stdout
#
absolutePath()
{
	if [ "${1#/}" = "$1" ]; then
		echo "$(pwd)/$1"
	else
		echo "$1"
	fi
}

# iptables config
#
# configIptablesNat source destination
#
# See configureNat
#
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

# Configure NAT
#
# configureNat source destination
#
configureNat()
{
	iptables -t nat -A POSTROUTING -s $1 ! -d $1 -j MASQUERADE
	configIptablesNat $1 > /etc/network/iptables.rules
	chmod 0600 /etc/network/iptables.rules
	sed -e '/^iface lo inet loopback$/a\
\	pre-up iptables-restore < /etc/network/iptables.rules' -i \
	    /etc/network/interfaces
}

# Create temporary installer directory
#
# createTempDir
#
# 'TMP' contains created directory
#
# See removeTempDir
#
createTempDir()
{
	TMP=$(mktemp -d /tmp/cloud-install.XXX)
}

# Detect dhcp server on network
#
# detectDhcpServer interface
#
# exit 0 if detected, >0 otherwise
#
detectDhcpServer()
{
	nmap --script broadcast-dhcp-discover -e $1 2> /dev/null \
	    | grep -q DHCPOFFER
}

# Disable blanking if on console
#
# disableBlank
#
# See enableBlank
#
disableBlank()
{
	tty=$(tty)
	if [ -n "$tty" ] && [ "${tty%%[0-9]}" = /dev/tty ]; then
		CONSOLE_BLANK=$(cat /sys/module/kernel/parameters/consoleblank)
		setterm -blank 0
	fi
}

# Re-enable blanking if on console
#
# enableBlank
#
# See disableBlank
#
enableBlank()
{
	if [ -n "$CONSOLE_BLANK" ]; then
		setterm -blank $((CONSOLE_BLANK/60))
	fi
}

# Enable IP forwarding
#
# enableIpForwarding
#
enableIpForwarding()
{
	sed -e 's/^#net.ipv4.ip_forward=1$/net.ipv4.ip_forward=1/' -i \
	    /etc/sysctl.conf
	sysctl -p
}

# Display error
#
# error
#
error()
{
	dialogMsgBox "[!] An error has occurred" Continue \
	    "Installation aborted\n\nSee /var/log/cloud-install.log for details." \
	    10 60
}

# Cleanup installer before exit
#
# exitInstall
#
exitInstall()
{
	ret=$?
	set +x
	stopLog
	wait
	if [ $ret -gt 0 ]; then
		error
	fi
	enableBlank
	removeTempDir
}

# Generate SSH keys for install user
#
# generateSshKeys
#
generateSshKeys()
{
	if [ ! -e "$INSTALL_HOME/.ssh/id_rsa" ]; then
	    sudo -u "$INSTALL_USER" ssh-keygen -N "" \
		 -f "$INSTALL_HOME/.ssh/id_rsa" 1>&2
	else
	    echo "*** ssh keys exist for this user, they will be used instead."
	    echo "*** If the current ssh keys are not passwordless you'll be"
	    echo "*** required to enter your ssh key password during juju"
	    echo "*** deployments."
	fi
}

# Get interfaces
#
# getInterfaces
#
# writes space delimited list to stdout
#
getInterfaces()
{
	ifconfig -s | egrep -v 'Iface|lo' | egrep -o '^[a-zA-Z0-9]+' | paste -sd ' '
}

# Get gateway
#
# gateway
#
gateway()
{
	route -n | awk 'index($4, "G") { print $2 }'
}

# Get IP address
#
# ipAddress interface
#
ipAddress()
{
	ifconfig $1 | egrep -o "inet addr:[0-9.]+" | sed -e "s/^inet addr://"
}

# Get IP broadcast address
#
# ipBroadcast interface
#
ipBroadcast()
{
	ifconfig $1 | egrep -o "Bcast:[0-9.]+" | sed -e "s/^Bcast://"
}

# Get IP netmask
#
# ipNetmask interface
#
ipNetmask()
{
	ifconfig $1 | egrep -o "Mask:[0-9.]+" | sed -e "s/^Mask://"
}

# Get IP network
#
# ipNetwork interface
#
ipNetwork()
{
	ip addr show $1 | awk '/^    inet / { print $2 }'
}

# Remove temporary installer directory
#
# removeTempDir
#
# See createTempDir
#
removeTempDir()
{
	if [ -n "$TMP" ]; then
		rm -rf "$TMP"
	fi
}

# Start external log
#
# startLog
#
# See stopLog
#
startLog()
{
	(umask 0077; touch "$LOG")
	printf "Cloud installation started %s\n" "$(date)" >> "$LOG"
	mkfifo -m 0600 "$TMP/log"
	ts "$TMP/log" >> "$LOG" &
	log_pid=$!
	exec 2> "$TMP/log"
}

# Stop external log
#
# stopLog
#
# See startLog
#
stopLog()
{
	if [ -n "$log_pid" ]; then
		exec 2>&1
		wait $log_pid
		rm -f "$TMP/log"
		printf "Cloud installation finished %s\n" "$(date)" >> "$LOG"
	fi
}

# Timestamp input
#
# ts file
#
# writes timestamped lines from file to stdout
#
# See startLog
#
ts()
{
	awk '{ print strftime("%F %T"), $0; fflush() }' "$1"
}

INSTALL_USER=${SUDO_USER:-root}
INSTALL_HOME=$(getent passwd $INSTALL_USER | cut -d: -f6)

# HELPER TOOLS
configure_landscape=/usr/share/cloud-installer/bin/configure-landscape
ip_range=/usr/share/cloud-installer/bin/ip_range.py
maas_report_boot_images=/usr/share/cloud-installer/bin/maas-report-boot-images

TEMPLATES=/usr/share/cloud-installer/templates
