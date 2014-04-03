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
TMP=$(mktemp -d /tmp/cloud-install.XXX)

export PYTHONPATH=/usr/share/cloud-installer/common
export PYTHONDONTWRITEBYTECODE=true

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
	whiptail --title "[!] An error has occurred" --backtitle "$BACKTITLE" \
	    --ok-button Continue \
	    --msgbox "Installation aborted\n\nSee /var/log/cloud-install.log for details." \
	    10 60
}

exitInstall()
{
	ret=$?
	stopLog
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

dialogInput()
{
	whiptail --title "$1" --backtitle "$BACKTITLE" --inputbox "$2" $3 $4 \
	    "$5" 3>&1 1>/dev/tty 2>&3 || true
}

dialogMenu()
{
	title=$1
	text=$2
	height=$3
	width=$4
	menu_height=$5
	shift 5
	for item; do
		echo "\"$item\""
		echo '""'
	done | xargs whiptail --title "$title" --backtitle "$BACKTITLE" --menu \
	    "$text" $height $width $menu_height 3>&1 1>/dev/tty 2>&3 || true
}

dialogYesNo()
{
	whiptail --title "$1" --backtitle "$BACKTITLE" --yesno "$2" $3 $4
}

dialogMsgBox()
{
	whiptail --title "$1" --backtitle "$BACKTITLE" --ok-button "$2" \
	    --msgbox "$3" $4 $5
}

dialogPassword()
{
	whiptail --title "$1" --backtitle "$BACKTITLE" --passwordbox "$2" $3 \
	    $4 3>&1 1>/dev/tty 2>&3 || true
}

getInterfaces()
{
	ifconfig -s | egrep -v 'Iface|lo' | egrep -o '^[a-zA-Z0-9]+' | paste -sd ' '
}

gateway()
{
	route -n | awk 'index($4, "G") { print $2 }'
}

ipAddress()
{
	ifconfig $1 | egrep -o "inet addr:[0-9.]+" | sed -e "s/^inet addr://"
}

ipBroadcast()
{
	ifconfig $1 | egrep -o "Bcast:[0-9.]+" | sed -e "s/^Bcast://"
}

ipNetmask()
{
	ifconfig $1 | egrep -o "Mask:[0-9.]+" | sed -e "s/^Mask://"
}

ipNetwork()
{
	ip addr show $1 | awk '/^    inet / { print $2 }'
}

startLog()
{
	(umask 0077; touch "$LOG")
	printf "Cloud installation started %s\n" "$(date)" >> "$LOG"
	mkfifo -m 0600 "$TMP/log"
	ts "$TMP/log" >> "$LOG" &
	exec 2> "$TMP/log"
}

stopLog()
{
	exec 2>&1
	rm -f "$TMP/log"
	printf "Cloud installation finished %s\n" "$(date)" >> "$LOG"
}

ts()
{
	awk '{ print strftime("%F %T"), $0 }' "$1"
}

INSTALL_USER=$(getent passwd 1000 | cut -d : -f 1)

# HELPER TOOLS
wait_for_landscape=/usr/share/cloud-installer/bin/wait-for-landscape
ip_range=/usr/share/cloud-installer/bin/ip_range.py
