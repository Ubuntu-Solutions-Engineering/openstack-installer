#
# configure.sh - install configuration
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

MULTI_DISK_MIN=10
MULTI_RAM_MIN=2
SINGLE_DISK_MIN=20
SINGLE_RAM_MIN=8

checkDiskSpace()
{
	avail=$(df -B G --total -l --output=avail -x devtmpfs -x tmpfs \
	    | tail -n 1 | tr -d " G")
	if [ $avail -lt $1 ]; then
		fail=$((fail + 1))
		text="$text[!!] You need at least ${1}GB of disk space\n\n"
	fi
}

checkMemory()
{
	free=$(free -gt | awk 'END { print $2 }')
	if [ $free -lt $1 ]; then
		fail=$((fail + 1))
		text="$text[!!] You need at least ${1}GB of memory\n\n"
	fi
}

checkMultiInstall()
{
	fail=0
	text=""
	checkMemory $MULTI_RAM_MIN
	checkDiskSpace $MULTI_DISK_MIN
}

checkSingleInstall()
{
	fail=0
	text=""
	checkMemory $SINGLE_RAM_MIN
	checkDiskSpace $SINGLE_DISK_MIN
}

getDomain() {
	echo "$1" | grep -E "^[^@]+@[^@]+\.[^@]+$" | sed -E -e 's/[^@]+@([^@]+\.[^@]+)/\1/'
}

configureInstall()
{
	state=1
	while [ -n "$state" ] && [ "$state" != 32 ]; do
		next_state=$((state + 1))
		case $state in
		1)
			if [ -z "$install_type" ]; then
			    dialogMenu "Select install type" "" 10 60 3 \
				Multi-system "Single system" "Landscape managed"
			    install_type=$input
			    if [ $ret -ne 0 ]; then
				popState; continue
			    fi
			fi
			case $install_type in
			Multi-system)
				next_state=10
				;;
			"Single system")
				next_state=20
				;;
			"Landscape managed")
				next_state=10
				;;
			esac
			;;
		10)
			checkMultiInstall
			if [ $fail -ne 0 ] && ! requirementsError; then
				popState; continue
			fi
			state=11; continue
			;;
		11)
			if [ ! -z "$interface" ]; then
			    state=$next_state;
			    continue
			fi
			interfaces=$(getInterfaces)
			interfaces_count=$(echo "$interfaces" | wc -w)
			if [ $interfaces_count -ge 2 ]; then
				dialogMenu "Select the network" \
				    "Select the network MaaS will manage. MaaS will be the DHCP server on this network and respond to PXE requests." \
				    15 60 6 $interfaces
				interface=$input
				if [ $ret -ne 0 ]; then
					popState; continue
				fi
			else
				interface=$interfaces
				state=$next_state; continue
			fi
			;;
		12)
			if [ ! -z "$skip_dhcp_detection" ]; then
			    state=$next_state; continue
			fi
			dialogGaugeStart "DHCP server detection" \
			    "Detecting existing dhcp servers...\n\nPress [enter] to skip" \
			    8 70 0
			detectDhcpServer $interface &
			skip=""
			i=0
			while [ $i -ne 10 ]; do
				if dd bs=1 iflag=nonblock 2> /dev/null \
				    | tr "\r" "\n" | read -r input; then
					skip=true
					{ kill $!; wait $!; } || true
					break
				fi
				if ! ps -p $! > /dev/null; then
					break
				fi
				echo $(((i * 100) / 10))
				sleep 1
				i=$((i + 1))
			done > "$TMP/gauge"
			dialogGaugeStop
			if [ -z "$skip" ] && wait $! && ! dialogYesNo "[!] Existing DHCP server detected" \
			    Continue Cancel \
			    "An existing DHCP server has been detected on the interface ${interface}.\n\nThis installation will install and manage its own DHCP server. A collision between servers may prevent you from adding subsequent nodes.\n\nSelect Continue to proceed regardless" \
			    15 60; then
				popState; continue
			fi
			state=13; continue
			;;
		13)
			if [ ! -z "$bridge_interface" ]; then
			    state=$next_state; continue
			fi
			if [ $interfaces_count -ge 2 ]; then
				if dialogYesNo "Bridge interface?" Yes No \
				    "Sometimes it is useful to run MaaS on its own network. If you are running MaaS on its own network and would like to bridge this network to the outside world, please indicate so." \
				    10 60; then
					bridge_interface=true
				fi
			fi
			state=$next_state; continue
			;;
		14)
			if [ ! -z "$dhcp_range" ]; then
			    dhcp_range_was_preset=true
			    state=$next_state; continue
			fi
			network=$(ipNetwork $interface)
			address=$(ipAddress $interface)
			if [ -z "$address" ]; then
				# The interface isn't configured, so don't suggest a DHCP range.
				dhcp_range=""
			elif [ -n "$bridge_interface" ]; then
				dhcp_range=$($ip_range $network $address)
			else
				gateway=$(gateway)
				dhcp_range=$($ip_range $network $address $gateway)
			fi
			state=$next_state; continue
			;;
		15)
			if [ -z "$dhcp_range_was_preset" ]; then

			    dialogInput "IP address range (<ip addr low>-<ip addr high>):" \
				"IP address range for DHCP leases.\nNew nodes will be assigned addresses from this pool." \
				10 60 "$dhcp_range"
			    dhcp_range=$input
			    if [ $ret -ne 0 ]; then
				popState; continue
			    fi
			fi
			if [ "$install_type" = "Landscape managed" ]; then
				next_state=16
			else
				next_state=30
			fi
			;;
		16)
			if [ -z "$admin_email" ]; then

			    dialogInput "Landscape login" "Please enter the login email you would like to use for Landscape." 10 60
			    admin_email=$input
			fi
			result=$(getDomain "$admin_email")
			if [ -z "$result" ]; then
				popState; continue
			fi
			email_domain="$result"
			;;
		17)
			if [ ! -z "$admin_name" ]; then
			    continue
			fi

			suggested_name="$(getent passwd $INSTALL_USER | cut -d ':' -f 5 | cut -d ',' -f 1)"
			dialogInput "Landscape user's full name" "Please enter the full name of the admin user for Landscape." 10 60 "$suggested_name"
			admin_name=$input

			if [ -z "$admin_name" ]; then
				popState; continue
			fi
			;;
		18)
			if [ -z "$system_email" ]; then
			    dialogInput "Landscape system email" "Please enter the email that landscape should use as the system email." 10 60 "landscape@$email_domain"
			    system_email=$input
			    result=$(getDomain "$system_email")
			    if [ -z "$result" ]; then
				popState; continue
			    fi
			fi
			next_state=30
			;;
		20)
			checkSingleInstall
			if [ $fail -ne 0 ] && ! requirementsError; then
				popState; continue
			fi
			state=30; continue
			;;
		30)
			if [ ! -z "$openstack_password" ]; then
			    # skip to end
			    state=32; continue
			fi
			dialogPassword "OpenStack admin user password:" \
			    "A good password will contain a mixture of letters, numbers and punctuation and should be changed at regular intervals." \
			    10 60
			openstack_password=$input
			if [ $ret -ne 0 ]; then
				popState; continue
			fi
			;;
		31)
			dialogPassword "OpenStack admin user password to verify:" \
			    "Please enter the same OpenStack admin user password again to verify that you have typed it correctly." \
			    10 60
			openstack_password2=$input
			if [ $ret -ne 0 ]; then
				popState; continue
			fi
			if [ "$openstack_password" != "$openstack_password2" ]; then
				dialogMsgBox "[!] Password mismatch" Continue \
				    "The two passwords you entered were not the same, please try again." \
				    10 60
				popState; continue
			fi
			;;
		esac
		pushState "$state"
		state=$next_state
	done
}

popState()
{
	if [ -n "$states" ]; then
		state=${states##* }
		states=${states% *}
	else
		state=""
	fi
}

pushState()
{
	states="$states $1"
}

requirementsError()
{
	dialogYesNo "[!] System requirements not met" Continue Cancel \
	    "The following system requirements are not met for $install_type install:\n\n${text}Select Continue to proceed regardless" \
	    $((11 + (2 * fail))) 60
}
