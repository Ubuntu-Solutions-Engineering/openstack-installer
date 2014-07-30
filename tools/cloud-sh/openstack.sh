#!/bin/sh -ex

CORES=$((1 + ((($(grep processor /proc/cpuinfo | wc -l) - 1) * 3) / 4)))

agentState()
{
	juju status | python -c "import yaml; import sys; print yaml.load(sys.stdin)[\"machines\"][\"$1\"][\"agent-state\"]" 2> /dev/null
}

agentStateUnit()
{
	juju status | python -c "import yaml; import sys; print yaml.load(sys.stdin)[\"services\"][\"$1\"][\"units\"][\"$1/$2\"][\"agent-state\"]" 2> /dev/null
}

configOpenrc()
{
	cat <<-EOF
		export OS_USERNAME=$1
		export OS_PASSWORD=$2
		export OS_TENANT_NAME=$3
		export OS_AUTH_URL=$4
		export OS_REGION_NAME=$5
		EOF
}

unitAddress()
{
	juju status | python -c "import yaml; import sys; print yaml.load(sys.stdin)[\"services\"][\"$1\"][\"units\"][\"$1/$2\"][\"public-address\"]" 2> /dev/null
}

unitMachine()
{
	juju status | python -c "import yaml; import sys; print yaml.load(sys.stdin)[\"services\"][\"$1\"][\"units\"][\"$1/$2\"][\"machine\"]" 2> /dev/null
}

waitForMachine()
{
	for machine; do
		while [ "$(agentState $machine)" != started ]; do
			sleep 5
		done
	done
}

waitForService()
{
	for service; do
		while [ "$(agentStateUnit "$service" 0)" != started ]; do
			sleep 5
		done
	done
}

juju bootstrap
waitForMachine 0

juju add-machine --constraints "cpu-cores=$CORES mem=4G root-disk=20G"

juju add-machine --constraints "cpu-cores=$CORES mem=1G"
juju deploy --config config.yaml --to 2 quantum-gateway

juju add-machine --constraints "cpu-cores=$CORES mem=2G root-disk=20G"
juju deploy --config config.yaml --to 3 nova-compute

waitForMachine 1
juju scp lxc-network.sh 1:
juju run --machine 1 "sudo ./lxc-network.sh"
juju deploy --config config.yaml --to lxc:1 mysql
juju deploy --to lxc:1 rabbitmq-server
juju deploy --config config.yaml --to lxc:1 keystone
juju deploy --config config.yaml --to lxc:1 nova-cloud-controller
#juju deploy --to lxc:1 cinder
juju deploy --to lxc:1 glance
juju deploy --to lxc:1 openstack-dashboard

# relation must be set first
# no official way of knowing when this relation hook will fire
waitForService mysql keystone
juju add-relation keystone mysql
sleep 120

juju add-relation nova-cloud-controller mysql
juju add-relation nova-cloud-controller rabbitmq-server
juju add-relation nova-cloud-controller glance
juju add-relation nova-cloud-controller keystone
juju add-relation quantum-gateway mysql
juju add-relation quantum-gateway rabbitmq-server
juju add-relation quantum-gateway nova-cloud-controller
#juju add-relation cinder nova-cloud-controller
#juju add-relation cinder mysql
#juju add-relation cinder rabbitmq-server
juju add-relation nova-compute mysql
juju add-relation nova-compute:amqp rabbitmq-server:amqp
juju add-relation nova-compute glance
juju add-relation nova-compute nova-cloud-controller
juju add-relation glance mysql
juju add-relation glance keystone
juju add-relation openstack-dashboard keystone

waitForService rabbitmq-server nova-cloud-controller glance openstack-dashboard quantum-gateway nova-compute
# no official way of knowing when relation hooks have fired
sleep 120

# correct quantum networking for 1 nic
machine=$(unitMachine quantum-gateway 0)
juju scp quantum-network.sh $machine:
juju run --machine $machine "sudo ./quantum-network.sh"

mkdir -m 0700 -p cloud
controller_address=$(unitAddress keystone 0)
configOpenrc admin password admin http://$controller_address:5000/v2.0 RegionOne > cloud/admin-openrc
configOpenrc ubuntu password ubuntu http://$controller_address:5000/v2.0 RegionOne > cloud/ubuntu-openrc
chmod 0600 cloud/*

machine=$(unitMachine nova-cloud-controller 0)
juju scp cloud-setup.sh cloud/admin-openrc cloud/ubuntu-openrc ~/.ssh/id_rsa.pub $machine:
juju run --machine $machine ./cloud-setup.sh

machine=$(unitMachine glance 0)
juju scp glance.sh cloud/admin-openrc $machine:
juju run --machine $machine ./glance.sh
