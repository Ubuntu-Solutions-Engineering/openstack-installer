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

# Check free disk space
#
# checkDiskSpace minimum
#
# 'fail' contains current failure count
# 'text' contains error message
#
# See requirementsError
#
checkDiskSpace()
{
	avail=$(df -B G --total -l --output=avail -x devtmpfs -x tmpfs \
	    | tail -n 1 | tr -d " G")
	if [ $avail -lt $1 ]; then
		fail=$((fail + 1))
		text="$text[!!] You need at least ${1}GB of disk space\n\n"
	fi
}

# Check total memory
#
# checkMemory minimum
#
# 'fail' contains current failure count
# 'text' contains error message
#
# See requirementsError
#
checkMemory()
{
	free=$(free -gt | awk 'END { print $2 }')
	if [ $free -lt $1 ]; then
		fail=$((fail + 1))
		text="$text[!!] You need at least ${1}GB of memory\n\n"
	fi
}

# Check multi install requirements
#
# checkMultiInstall
#
# 'fail' contains current failure count
# 'text' contains error message
#
# See requirementsError
#
checkMultiInstall()
{
	fail=0
	text=""
	checkMemory $MULTI_RAM_MIN
	checkDiskSpace $MULTI_DISK_MIN
}

# Check single install requirements
#
# checkSingleInstall
#
# 'fail' contains current failure count
# 'text' contains error message
#
# See requirementsError
#
checkSingleInstall()
{
	fail=0
	text=""
	checkMemory $SINGLE_RAM_MIN
	checkDiskSpace $SINGLE_DISK_MIN
}

# Get email domain
#
# getDomain email
#
getDomain()
{
	echo "$1" | grep -E "^[^@]+@[^@]+\.[^@]+$" \
	    | sed -E -e 's/[^@]+@([^@]+\.[^@]+)/\1/'
}

# Validate DHCP range
#
# validateDHCPRange range
#
# 'ret' contains exit code (0 on success, >0 otherwise)
#
validateDHCPRange() 
{
	{ python3 -c "from ipaddress import ip_address; import sys; addrs = list(map(ip_address, '$1'.split('-'))); addrs[1]" \
	    > /dev/null ; ret=$?; } || true
}

# Configure install
#
# configureInstall
#
# 'install_type' and other variables will contain user specified configuration
# 'install_type' will be empty if user cancels
#
# 'ret' contains exit code (0 on success, >0 if user cancels)
#
configureInstall()
{
	determineSeeds
	configureMenu
}

# Configure Menu
#
# configureMenu
#
# 'ret' contains exit code (0 on success, >0 if user cancels)
#
# See configureInstall
#
configureMenu()
{
	state=1
	while [ -n "$state" ] && [ "$state" != 32 ]; do
		next_state=$((state + 1))
		case $state in

		## install type ##
		1)
			if [ -n "$seed_install_type" ]; then
				state=$next_state; continue
			fi
			dialogMenu "Select install type" "$install_type" "" 10 \
			    60 3 Multi-system "Single system" \
			    "Landscape managed"
			install_type=$input
			if [ $ret -ne 0 ]; then
				popState; continue
			fi
			;;
		2)
			case $install_type in
			Multi-system|"Landscape managed")
				state=10
				;;
			"Single system")
				state=20
				;;
			esac
			continue
			;;

		## multi requirements ##
		10)
			if [ "$skip_requirement_checks" != true ]; then
				checkMultiInstall
				if [ $fail -ne 0 ] && ! requirementsError; then
					popState; continue
				fi
			fi
			state=$next_state; continue
			;;

		## interface selection ##
		11)
			if [ -n "$seed_interface" ]; then
				state=$next_state; continue
			fi
			interfaces=$(getInterfaces)
			interfaces_count=$(echo "$interfaces" | wc -w)
			if [ $interfaces_count -ge 2 ]; then
				dialogMenu "Select the network" "" \
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

		## dhcp detection ##
		12)
			if [ "$skip_dhcp_detection" = true ]; then
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
			state=$next_state; continue
			;;

		## bridge interface ##
		13)
			if [ -z "$seed_bridge_interface" ]; then
				interfaces_count=$(getInterfaces | wc -w)
				if [ $interfaces_count -ge 2 ] && dialogYesNo \
				    "Bridge interface?" Yes No \
				    "Sometimes it is useful to run MaaS on its own network. If you are running MaaS on its own network and would like to bridge this network to the outside world, please indicate so." \
				    10 60; then
					bridge_interface=true
				else
					bridge_interface=false
				fi
			fi
			state=$next_state; continue
			;;

		## dhcp range ##
		14)
			if [ -n "$seed_dhcp_range" ]; then
				state=$((next_state + 1)); continue
			fi
			network=$(ipNetwork $interface)
			address=$(ipAddress $interface)
			if [ -z "$address" ]; then
				# The interface isn't configured, so don't suggest a DHCP range.
				dhcp_range=""
			elif [ "$bridge_interface" = true ]; then
				dhcp_range=$($ip_range $network $address)
			else
				gateway=$(gateway)
				dhcp_range=$($ip_range $network $address $gateway)
			fi
			state=$next_state; continue
			;;
		15)
			dialogInput "IP address range (<ip addr low>-<ip addr high>):" \
			    "IP address range for DHCP leases.\nNew nodes will be assigned addresses from this pool." \
			    10 60 "$dhcp_range"
			dhcp_range=$input
			if [ $ret -ne 0 ]; then
				popState; continue
			fi
			validateDHCPRange $dhcp_range
			if [ -z "$dhcp_range" ] || [ $ret -eq 1 ]; then
				dialogMsgBox "[!] Invalid Range" Continue \
				    "Please enter a valid IP address range" 10 60
				continue
			fi
			;;
		16)
			if [ "$install_type" = "Multi-system" ]; then
				state=30
			else
				state=$next_state
			fi
			continue
			;;

		## landscape email ##
		17)
			if [ -n "$seed_admin_email" ]; then
				email_domain=$(getDomain "$admin_email")
				state=$next_state; continue
			fi
			dialogInput "Landscape login" \
			    "Please enter the login email you would like to use for Landscape." \
			    10 60
			admin_email=$input
			if [ $ret -ne 0 ]; then
				popState; continue
			fi
			if [ -z "$admin_email" ]; then
				dialogMsgBox "[!] Missing Input" Continue \
				    "Please enter a login email." 10 60
				continue
			fi
			email_domain=$(getDomain "$admin_email")
			if [ -z "$email_domain" ]; then
				dialogMsgBox "[!] Missing Email Domain" \
				    Continue \
				    "Sorry, I couldn't extract the domain from '$admin_email'. Please try again." \
				    10 60
				continue
			fi
			;;

		## landscape name ##
		18)
			if [ -n "$seed_admin_name" ]; then
				state=$next_state; continue
			fi
			suggested_name="$(getent passwd $INSTALL_USER | cut -d ':' -f 5 | cut -d ',' -f 1)"
			dialogInput "Landscape user's full name" \
			    "Please enter the full name of the admin user for Landscape." \
			    10 60 "$suggested_name"
			admin_name=$input
			if [ $ret -ne 0 ]; then
				popState; continue
			fi
			if [ -z "$admin_name" ]; then
				dialogMsgBox "[!] Missing Input" Continue \
				    "Please enter a name." 10 60
				continue
			fi
			;;

		## landscape system email ##
		19)
			if [ -n "$seed_system_email" ]; then
				state=30; continue
			fi
			dialogInput "Landscape system email" \
			    "Please enter the email that landscape should use as the system email." \
			    10 60 "landscape@$email_domain"
			system_email=$input
			if [ $ret -ne 0 ]; then
				popState; continue
			fi
			if [ -z "$system_email" ]; then
				dialogMsgBox "[!] Missing Input" \
				    Continue "Please enter a system email." 10 \
				    60
				continue
			fi
			result=$(getDomain "$system_email")
			if [ -z "$result" ]; then
				dialogMsgBox "[!] Missing Email Domain" \
				    Continue \
				    "Sorry, I could not extract the domain from '$system_email'. Please try again." \
				    10 60
				continue
			fi
			next_state=30
			;;

		## single requirements ##
		20)
			if [ "$skip_requirement_checks" != true ]; then
				checkSingleInstall
				if [ $fail -ne 0 ] && ! requirementsError; then
					popState; continue
				fi
			fi
			state=30; continue
			;;

		## openstack password ##
		30)
			if [ -n "$seed_openstack_password" ]; then
				state=$((next_state + 1)); continue
			fi
			dialogPassword "OpenStack admin user password:" \
			    "A good password will contain a mixture of letters, numbers and punctuation." \
			    10 60
			openstack_password=$input
			if [ $ret -ne 0 ]; then
				popState; continue
			fi
			if [ -z "$openstack_password" ]; then
				dialogMsgBox "[!] Missing Password" Continue \
				    "Please enter a password." 10 60
				continue
			fi
			;;

		## openstack password confirmation ##
		31)
			dialogPassword "OpenStack admin user password to verify:" \
			    "Please enter the same OpenStack admin user password again to verify." \
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
			state=$next_state; continue
			;;

		esac
		pushState "$state"
		state=$next_state
	done
	if [ -n "$state" ]; then
		ret=0
	else
		ret=1
	fi
}

# Determine preseeded config
#
# determineSeeds
#
# See configureInstall
#
determineSeeds()
{
	# general
	[ -n "$install_type" ] && seed_install_type=true
	[ -n "$openstack_password" ] && seed_openstack_password=true

	# multi install
	[ -n "$bridge_interface" ] && seed_bridge_interface=true
	[ -n "$dhcp_range" ] && seed_dhcp_range=true
	[ -n "$interface" ] && seed_interface=true

	# landscape install
	[ -n "$admin_email" ] && seed_admin_email=true
	[ -n "$admin_name" ] && seed_admin_name=true
	[ -n "$system_email" ] && seed_system_email=true

	return 0
}

# Pop menu state
#
# popState
#
# 'state' contains popped state
#
# See pushState
#
popState()
{
	if [ -n "$states" ]; then
		state=${states##* }
		states=${states% *}
	else
		state=""
	fi
}

# Push menu state
#
# pushState state
#
# See popState
#
pushState()
{
	states="$states $1"
}

# Display requirements errors
#
# requirementsError
#
# exit 0 on continue, 1 on cancel
#
# See checkMultiInstall, checkSingleInstall
#
requirementsError()
{
	dialogYesNo "[!] System requirements not met" Continue Cancel \
	    "The following system requirements are not met for $install_type install:\n\n${text}Select Continue to proceed regardless" \
	    $((11 + (2 * fail))) 60
}
