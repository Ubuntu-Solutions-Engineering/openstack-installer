#
# display.sh - display routines for cloud-install
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

# Install packages via apt-get displaying progress within an existing gauge
#
# dialogAptInstall percent range
#
# See dialogGaugeStart
#
dialogAptInstall()
{
	download_start=$1
	download_range=$(($2 / 2))
	install_start=$((download_start + download_range))
	install_range=$(($2 - download_range))
	shift 2
	mkfifo -m 0600 "$TMP/apt-status"
	DEBIAN_FRONTEND=noninteractive apt-get -qyf \
	    -o Dpkg::Options::=--force-confdef \
	    -o Dpkg::Options::=--force-confold \
	    -o APT::Status-Fd=3 install "$@" \
	    < /dev/null 1>&2 \
	    3> "$TMP/apt-status" &
	while IFS=: read status pkg percent description; do
		case $status in
		dlstatus)
			text="Downloading packages...$description"
			p=$((download_start + ((${percent%.*} * download_range) / 100)))
			;;
		pmstatus)
			text="Installing packages...$description"
			p=$((install_start + ((${percent%.*} * install_range) / 100)))
			;;
		*)
			echo "unexpected apt-get status $status" 1>&2
			exit 1
			;;
		esac
		dialogGaugePrompt $p "$text"
	done < "$TMP/apt-status"
	wait $!
	rm -f "$TMP/apt-status"
}

# Update a progress gauge
#
# dialogGaugePrompt percent text
#
# See dialogGaugeStart
#
dialogGaugePrompt()
{
	printf "%s\n%s\n%s\n%s\n" XXX $1 "$2" XXX
}

# Start a progress gauge
#
# dialogGaugeStart title text height width percent
#
# See dialogGaugePrompt, dialogGaugeStop
#
dialogGaugeStart()
{
	mkfifo -m 0600 "$TMP/gauge"
	whiptail --title "$1" --backtitle "$BACKTITLE" --gauge "$2" $3 $4 $5 \
	    < "$TMP/gauge" &
	gauge_pid=$!
}

# Stop a progress gauge
#
# See dialogGaugeStart
#
dialogGaugeStop()
{
	wait $gauge_pid
	rm -f "$TMP/gauge"
}

# Display an input box
#
# dialogInput title text height width input-text
#
# 'input' contains text entry
# 'ret' contains exit code (0 on success, >0 if user cancels)
#
dialogInput()
{
	{ input=$(whiptail --title "$1" --backtitle "$BACKTITLE" --inputbox \
	    "$2" $3 $4 "$5" 3>&1 1>/dev/tty 2>&3); ret=$?; } || true
}

# Display a menu
#
# dialogMenu title default-item text height width menu-height menu-item...
#
# 'input' contains menu selection
# 'ret' contains exit code (0 on success, >0 if user cancels)
#
dialogMenu()
{
	title=$1
	default_item=$2
	text=$3
	height=$4
	width=$5
	menu_height=$6
	shift 6
	{
		input=$(for item; do echo "\"$item\""; echo '""'; done \
		    | xargs whiptail --title "$title" --backtitle "$BACKTITLE" \
		    --default-item "$default_item" --menu "$text" $height \
		    $width $menu_height 3>&1 1>/dev/tty 2>&3)
		ret=$?
	} || true
}

# Display a message
#
# dialogMsgBox title button-text text height width
#
dialogMsgBox()
{
	whiptail --title "$1" --backtitle "$BACKTITLE" --ok-button "$2" \
	    --msgbox "$3" $4 $5
}

# Display a password box
#
# dialogPassword title text height width
#
# 'input' contains text entry
# 'ret' contains exit code (0 on success, >0 if user cancels)
#
dialogPassword()
{
	{ input=$(whiptail --title "$1" --backtitle "$BACKTITLE" --passwordbox \
	    "$2" $3 $4 3>&1 1>/dev/tty 2>&3); ret=$?; } || true
}

# Display a yes/no choice
#
# dialogYesNo title yes-text no-text text height width
#
# exit 0 on yes, 1 on no
#
dialogYesNo()
{
	whiptail --title "$1" --backtitle "$BACKTITLE" --yes-button "$2" \
	    --no-button "$3" --yesno "$4" $5 $6
}
