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

checkSingleInstall()
{
	fail=0
	text=""
	checkMemory $SINGLE_RAM_MIN
	checkDiskSpace $SINGLE_DISK_MIN
}

configureInstall()
{
	state=1
	while [ -n "$state" ] && [ "$state" != 32 ]; do
		next_state=$((state + 1))
		case $state in
		1)
			install_type=$(dialogMenu "Select install type" "" 10 60 3 Multi-system "Single system" "Landscape managed")
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
			*)
				popState; continue
				;;
			esac
			;;
		10)
			interfaces=$(getInterfaces)
			interfaces_count=$(echo "$interfaces" | wc -w)
			if [ $interfaces_count -ge 2 ]; then
				interface=$(dialogMenu "Select network interface" "" 15 60 8 $interfaces)
				if [ -z "$interface" ]; then
					popState; continue
				fi
			else
				interface=$interfaces
				state=$next_state; continue
			fi
			;;
		11)
			bridge_interface=""
			if [ $interfaces_count -ge 2 ]; then
				if dialogYesNo "Bridge interface?" Yes No "Sometimes it is useful to run MaaS on its own network. If you are running MaaS on its own network and would like to bridge this network to the outside world, please indicate so." 10 60; then
					bridge_interface=true
				fi
			fi
			state=$next_state; continue
			;;
		12)
			network=$(ipNetwork $interface)
			address=$(ipAddress $interface)
			if [ -n "$bridge_interface" ]; then
				dhcp_range=$($ip_range $network $address)
			else
				gateway=$(gateway)
				dhcp_range=$($ip_range $network $address $gateway)
			fi
			state=$next_state; continue
			;;
		13)
			dhcp_range=$(dialogInput "IP address range (<ip addr low>-<ip addr high>):" "IP address range for DHCP leases.\nNew nodes will be assigned addresses from this pool." 10 60 "$dhcp_range")
			if [ -z "$dhcp_range" ]; then
				popState; continue
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
			openstack_password=$(dialogPassword "OpenStack admin user password:" "A good password will contain a mixture of letters, numbers and punctuation and should be changed at regular intervals." 10 60)
			if [ -z "$openstack_password" ]; then
				popState; continue
			fi
			;;
		31)
			openstack_password2=$(dialogPassword "OpenStack admin user password to verify:" "Please enter the same OpenStack admin user password again to verify that you have typed it correctly." 10 60)
			if [ -z "$openstack_password2" ]; then
				popState; continue
			fi
			if [ "$openstack_password" != "$openstack_password2" ]; then
				dialogMsgBox "[!] Password mismatch" Continue "The two passwords you entered were not the same, please try again." 10 60
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
	    "${text}Select Continue to proceed regardless" $((8 + (2 * fail))) \
	    60
}
