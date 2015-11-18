#!/bin/bash -ex

# NOTE: this script exits on errors and will be re-run if it returns
# any error value, so please ensure that commands are either safe to
# run multiple times or are guarded.

. /tmp/openstack-admin-rc

if [[ "$2" == "Single" ]]; then
    # configure external network for Single install path
    {% if openstack_release in ['icehouse', 'juno'] %}
    neutron net-show ext-net || neutron net-create --router:external=True ext-net
    {% else %}
    neutron net-show ext-net || neutron net-create --router:external ext-net
    {% endif %}
    neutron subnet-show ext-subnet || neutron subnet-create --name ext-subnet --gateway 10.0.{{N}}.1 --allocation-pool start=10.0.{{N}}.200,end=10.0.{{N}}.254 --disable-dhcp ext-net 10.0.{{N}}.0/24
fi

# adjust tiny image
nova flavor-delete m1.tiny || true

# create ubuntu user
keystone tenant-get ubuntu || keystone tenant-create --name ubuntu --description "Created by Juju"
keystone user-get ubuntu || keystone user-create --name ubuntu --tenant ubuntu --pass "$1" --email juju@localhost
keystone user-role-list --user ubuntu --tenant ubuntu | grep -q "Member" || keystone user-role-add --user ubuntu --role Member --tenant ubuntu

. /tmp/openstack-ubuntu-rc

# create vm network on Single only
if [[ "$2" == "Single" ]]; then
    neutron net-show ubuntu-net || neutron net-create ubuntu-net
    neutron subnet-show ubuntu-subnet || neutron subnet-create --name ubuntu-subnet --gateway 10.0.5.1 --dns-nameserver 10.0.{{N}}.1 ubuntu-net 10.0.5.0/24
    neutron router-show ubuntu-router || neutron router-create ubuntu-router
    neutron router-interface-add ubuntu-router ubuntu-subnet || true
    neutron router-gateway-set ubuntu-router ext-net # OK to run multiple times

    # create pool of at least 5 floating ips
    existingips=$(neutron floatingip-list -f csv | wc -l) # this number will include a header line
    to_create=$((6 - existingips))
    i=0
    while [ $i -ne $to_create ]; do
      neutron floatingip-create ext-net
      i=$((i + 1))
    done
fi

# configure security groups
neutron security-group-rule-create --direction ingress --ethertype IPv4 --protocol icmp --remote-ip-prefix 0.0.0.0/0 default || true
neutron security-group-rule-create --direction ingress --ethertype IPv4 --protocol tcp --port-range-min 22 --port-range-max 22 --remote-ip-prefix 0.0.0.0/0 default || true


# import key pair
nova keypair-show ubuntu-keypair || nova keypair-add --pub-key /tmp/id_rsa.pub ubuntu-keypair
