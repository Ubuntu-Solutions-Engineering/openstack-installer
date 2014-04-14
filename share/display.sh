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
			message="Downloading packages...$description"
			p=$((download_start + ((${percent%.*} * download_range) / 100)))
			;;
		pmstatus)
			message="Installing packages...$description"
			p=$((install_start + ((${percent%.*} * install_range) / 100)))
			;;
		*)
			echo "unexpected apt-get status $status" 1>&2
			exit 1
			;;
		esac
		dialogGaugePrompt $p "$message"
	done < "$TMP/apt-status"
	wait $!
	rm -f "$TMP/apt-status"
}

dialogGaugePrompt()
{
	printf "%s\n%s\n%s\n%s\n" XXX $1 "$2" XXX
}

dialogGaugeStart()
{
	mkfifo -m 0600 "$TMP/gauge"
	whiptail --title "$1" --backtitle "$BACKTITLE" --gauge "$2" $3 $4 $5 \
	    < "$TMP/gauge" &
	gauge_pid=$!
}

dialogGaugeStop()
{
	wait $gauge_pid
	rm -f "$TMP/gauge"
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

dialogYesNo()
{
	whiptail --title "$1" --backtitle "$BACKTITLE" --yesno "$2" $3 $4
}
