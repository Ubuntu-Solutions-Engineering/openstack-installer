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
		gaugePrompt $p "$message"
	done < "$TMP/apt-status"
	wait $!
	rm -f "$TMP/apt-status"
}
