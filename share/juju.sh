#
# juju.sh - Shell routines for Juju
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

configAgent()
{
	python - "$@" <<-"EOF"
		from collections import OrderedDict
		import sys
		from sys import argv

		import base64
		import yaml
		from yaml.dumper import Dumper

		class IgnoreAliasesDumper(Dumper):

		    def ignore_aliases(self, data):
		        return True

		def load_file(name):
		    with open(name, "rb") as f:
		        return base64.b64encode(f.read())

		def ordereddict_representer(dumper, data):
		    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())

		config = OrderedDict([("tag", argv[1]),
		                      ("nonce", argv[2]),
		                      ("cacert", load_file(argv[3])),
		                      ("stateaddresses", [argv[4]]),
		                      ("apiaddresses", [argv[5]]),
		                      ("oldpassword", argv[6]),
		                      ("values", OrderedDict([("CONTAINER_TYPE", ""),
		                                              ("LXC_BRIDGE", "br0"),
		                                              ("PROVIDER_TYPE", "maas")]))])
		if len(argv) > 7:
		    config.update(OrderedDict([("stateservercert", load_file(argv[7])),
		                               ("stateserverkey", load_file(argv[8])),
		                               ("apiport", int(argv[9]))]))
		yaml.add_representer(OrderedDict, ordereddict_representer)
		yaml.dump(config, sys.stdout, IgnoreAliasesDumper, default_flow_style=False)
		EOF
}

configAgentEnv()
{
	python <<-EOF
		from collections import OrderedDict
		import sys

		import yaml
		from yaml.dumper import Dumper

		class IgnoreAliasesDumper(Dumper):

		    def ignore_aliases(self, data):
		        return True

		def load_file(name):
		    with open(name, "rb") as f:
		        return f.read()

		def ordereddict_representer(dumper, data):
		    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())

		yaml.add_representer(OrderedDict, ordereddict_representer)
		yaml.dump(OrderedDict([("admin-secret", ""),
		                       ("agent-version", "$1"),
		                       ("api-port", 17070),
		                       ("authorized-keys", "$2"),
		                       ("ca-cert", load_file("$3")),
		                       ("ca-private-key", ""),
		                       ("default-series", "precise"),
		                       ("development", False),
		                       ("firewall-mode", "instance"),
		                       ("image-metadata-url", ""),
		                       ("logging-config", "<root>=DEBUG"),
		                       ("maas-agent-name", "$4"),
		                       ("maas-server", "$5"),
		                       ("name", "maas"),
		                       ("ssl-hostname-verification", True),
		                       ("state-port", 37017),
		                       ("tools-url", ""),
		                       ("type", "maas")]),
		          sys.stdout, IgnoreAliasesDumper, default_flow_style=False)
		EOF
}

configBootstrapNode()
{
	cat <<-EOF
		[
		    {
		        "status": 6,
		        "macaddress_set": [
		            {
		                "resource_uri": "/MAAS/api/1.0/nodes/node-juju-bootstrap/macs/00:00:5e:bb:bb:bb/",
		                "mac_address": "00:00:5e:bb:bb:bb"
		            }
		        ],
		        "hostname": "$1",
		        "power_type": "",
		        "routers": [],
		        "netboot": false,
		        "cpu_count": 1,
		        "storage": 0,
		        "system_id": "node-juju-bootstrap",
		        "architecture": "",
		        "memory": 1024,
		        "owner": "root",
		        "tag_names": [],
		        "ip_addresses": [],
		        "resource_uri": "/MAAS/api/1.0/nodes/node-juju-bootstrap/"
		    }
		]
		EOF
}

configJujuEnvironment()
{
	cat <<-EOF
		default: maas

		environments:
		  maas:
		    type: maas
		    maas-server: 'http://$1/MAAS/'
		    maas-oauth: '$2'
		    admin-secret: $3
		    default-series: precise
		    authorized-keys-path: ~/.ssh/id_rsa.pub
		EOF
}

configJujuTools()
{
	echo "{\"version\":\"$1\",\"url\":\"$2\",\"sha256\":\"$3\",\"size\":$4}"
}

configureBootstrapAgent()
{
	mkdir /var/lib/juju/agents/bootstrap
	echo "format 1.16" > /var/lib/juju/agents/bootstrap/format
	configAgent bootstrap user-admin:bootstrap \
	    "/home/$INSTALL_USER/.juju/maas-cert.pem" \
	    localhost:37017 localhost:17070 $4 /var/lib/juju/server.crt \
	    /var/lib/juju/server.key 17070 \
	    > /var/lib/juju/agents/bootstrap/agent.conf
	chmod 0600 /var/lib/juju/agents/bootstrap/agent.conf
	env_config=$(configAgentEnv ${3%%-*} \
	    "$(cat "/home/$INSTALL_USER/.ssh/id_rsa.pub")" \
	    "/home/$INSTALL_USER/.juju/maas-cert.pem" $2 http://$1/MAAS/ \
	    | base64 -w 0)
	/var/lib/juju/tools/$3/jujud bootstrap-state --data-dir /var/lib/juju \
	    --env-config $env_config --debug
	rm -rf /var/lib/juju/agents/bootstrap
}

configureJuju()
{
	mkdir -m 0700 "/home/$INSTALL_USER/.juju"
	configJujuEnvironment $1 $2 $3 \
	    > "/home/$INSTALL_USER/.juju/environments.yaml"
	chmod 0600 "/home/$INSTALL_USER/.juju/environments.yaml"
	chown -R -- "$INSTALL_USER:$INSTALL_USER" "/home/$INSTALL_USER/.juju"
}

configureJujuLogs()
{
	mkdir /var/log/juju
	cp /usr/share/cloud-install/juju/25-juju.conf /etc/rsyslog.d
	chmod 0600 /etc/rsyslog.d/25-juju.conf
	service rsyslog restart
}

configureMaasBootstrapNode()
{
	a2enmod rewrite
	cp /usr/share/cloud-install/juju/bootstrap.conf \
	    /etc/apache2/sites-available
	a2dissite 000-default
	a2ensite bootstrap
	configBootstrapNode $1 > /var/www/node-juju-bootstrap
	service apache2 restart
}

configureMachineAgent()
{
	mkdir -p /var/lib/juju/agents/machine-0
	echo "format 1.16" > /var/lib/juju/agents/machine-0/format
	configAgent machine-0 user-admin:bootstrap \
	    "/home/$INSTALL_USER/.juju/maas-cert.pem" \
	    localhost:37017 localhost:17070 $1 /var/lib/juju/server.crt \
	    /var/lib/juju/server.key 17070 \
	    > /var/lib/juju/agents/machine-0/agent.conf
	chmod 0600 /var/lib/juju/agents/machine-0/agent.conf
}

configureMongoDb()
{
	mkdir -m 0700 /var/lib/juju/db
	mkdir /var/lib/juju/db/journal
	for c in 0 1 2; do
		dd if=/dev/zero of=/var/lib/juju/db/journal/prealloc.$c \
		    bs=1M count=1
	done
	cp /usr/share/cloud-install/juju/juju-db.conf /etc/init
	service juju-db start 
}

configureProviderState()
{
	maas-upload-file http://localhost/MAAS/api/1.0 $2 $3-provider-state \
	    /usr/share/cloud-install/juju/provider-state
	url=http://$1$(maasFilePath $3-provider-state)
	echo $url > /tmp/provider-state-url
}

createJujuServerDirectory()
{
	mkdir /var/lib/juju
	echo "hostname: $1" > /var/lib/juju/MAASmachine.txt
}

# TODO this function should really be broken up into smaller functions
deployHostMachine()
{
	maas-cli maas nodes new architecture=amd64/generic \
	    mac_addresses=00:00:5e:cc:cc:cc hostname=juju-host
      cpu_count=$(grep -c processor /proc/cpuinfo) \
      memory=$(awk -F":" '$1~/MemTotal/{print $2/1024}' /proc/meminfo ) \
      storage=$(df | awk '$6~/\/$/{print $2/1024}')

	system_id=$(nodeSystemId 00:00:5e:cc:cc:cc)
	wget -O $TMP/maas.creds \
	    "http://localhost/MAAS/metadata/latest/by-id/$system_id/?op=get_preseed"
	maas-signal --config $TMP/maas.creds OK || true
	rm $TMP/maas.creds

	(cd "/home/$INSTALL_USER"; sudo -H -u "$INSTALL_USER" juju add-machine)
	# TODO There is a delay between adding a machine via the cli, which
	#      returns instantly, and the juju provisioning worker picking up
	#      the request and creating the necessary machine placeholder.
	#      Ideally we'd keep polling the output of juju status before
	#      proceeding. For now we just sleep.
	sleep 20
	password=$(pwgen -s 24)
	hash=$(jujuPassword $password)
	mongo --quiet --port 37017 \
	    --eval "db = db.getSiblingDB('juju'); db.machines.update({_id: '1'}, {\$set: {passwordhash: '$hash'}})" \
	    -u admin -p $2 --ssl admin
	mkdir /var/lib/juju/agents/machine-1
	echo "format 1.16" > /var/lib/juju/agents/machine-1/format
	nonce=$(mongo --quiet --port 37017 \
	    --eval "db = db.getSiblingDB('juju'); print(db.machines.findOne({_id: '1'}).nonce)" \
	    -u admin -p $2 --ssl admin)
	configAgent machine-1 $nonce "/home/$INSTALL_USER/.juju/maas-cert.pem" \
	    $1:37017 $1:17070 $password > /var/lib/juju/agents/machine-1/agent.conf
	chmod 0600 /var/lib/juju/agents/machine-1/agent.conf
	version=$(juju version)
	ln -s $version /var/lib/juju/tools/machine-1
	cp /usr/share/cloud-install/juju/jujud-machine-1.conf /etc/init
	service jujud-machine-1 start
}

disableMongoDbService()
{
	service mongodb stop || true
	echo 'ENABLE_MONGODB="no"' > /etc/default/mongodb
}

extractJujuTools()
{
	mkdir -p /var/lib/juju/tools/$3
	path=$(maasFilePath $2-tools/releases/juju-$3.tgz)
	wget -nv -O /var/lib/juju/tools/juju-$3.tgz http://localhost$path
	tar xzf /var/lib/juju/tools/juju-$3.tgz -C /var/lib/juju/tools/$3
	checksum=$(sha256sum /var/lib/juju/tools/juju-$3.tgz | cut -f 1 -d " ")
	size=$(stat -c %s /var/lib/juju/tools/juju-$3.tgz)
	configJujuTools $3 http://$1$path $checksum $size \
	    > /var/lib/juju/tools/$3/downloaded-tools.txt
	rm /var/lib/juju/tools/juju-$3.tgz
}

generateJujuCertificates()
{
	sudo -u "$INSTALL_USER" openssl req -newkey rsa:1024 -x509 \
	    -subj '/O=juju/CN=juju-generated CA for environment "maas"' \
	    -set_serial 0 -days 3650 -nodes \
	    -out "/home/$INSTALL_USER/.juju/maas-cert.pem" \
	    -keyout "/home/$INSTALL_USER/.juju/maas-private-key.pem"
	chmod 0600 "/home/$INSTALL_USER/.juju/maas-private-key.pem"
}

generateMongoDbCertificates()
{
	openssl req -newkey rsa:1024 -subj "/O=juju/CN=*" -nodes \
	    -out /var/lib/juju/server.req -keyout /var/lib/juju/server.key
	openssl x509 -req -CA "/home/$INSTALL_USER/.juju/maas-cert.pem" \
	    -CAkey "/home/$INSTALL_USER/.juju/maas-private-key.pem" \
	    -set_serial 0 -days 3650 -in /var/lib/juju/server.req \
	    -out /var/lib/juju/server.crt
	cat /var/lib/juju/server.crt /var/lib/juju/server.key \
	    > /var/lib/juju/server.pem
	chmod 0600 /var/lib/juju/server.key /var/lib/juju/server.pem
	rm /var/lib/juju/server.req
}

jujuBootstrap()
{
	generateJujuCertificates
	createJujuServerDirectory $2
	syncJujuTools
	agent_name=$(maasAgentName)
	version=$(juju version)
	extractJujuTools $1 $agent_name $version
	configureJujuLogs
	generateMongoDbCertificates
	old_password=$(jujuPassword $4)
	configureMachineAgent $old_password
	disableMongoDbService
	configureMongoDb
	configureProviderState $1 $3 $agent_name
	configureBootstrapAgent $1 $agent_name $version $old_password
	startMachineAgent $version
	configureMaasBootstrapNode $2
}

jujuPassword()
{
	python -c "from passlib.hash import pbkdf2_sha512; print pbkdf2_sha512.encrypt(\"$1\", salt=\"\x75\x82\x81\xca\", rounds=8192).split(\"\$\")[4][:24].replace(\".\", \"+\")"
}

maasAgentName()
{
	python -c "import yaml; print yaml.load(open(\"/home/$INSTALL_USER/.juju/environments/maas.jenv\"))[\"bootstrap-config\"][\"maas-agent-name\"]"
}

startMachineAgent()
{
	rm /var/lib/juju/server.crt /var/lib/juju/server.key
	ln -s $1 /var/lib/juju/tools/machine-0
	cp /usr/share/cloud-install/juju/jujud-machine-0.conf /etc/init
	service jujud-machine-0 start
}

syncJujuTools()
{
	(
		cd "/home/$INSTALL_USER"
		for c in 0 1 2; do
			if sudo -H -u "$INSTALL_USER" juju --show-log sync-tools --all; then
				exit 0
			fi
			sleep 5
		done
		exit 1
	)
}
