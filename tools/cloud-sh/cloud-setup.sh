#!/bin/sh -e

. ~/admin-openrc

# adjust tiny image
nova flavor-delete m1.tiny
nova flavor-create m1.tiny 1 512 8 1

# configure external network
neutron net-create --router:external=True --shared ext-net
neutron subnet-create --name ext-subnet --gateway 10.0.3.1 --allocation-pool start=10.0.3.200,end=10.0.3.254 --disable-dhcp ext-net 10.0.3.0/24

# create ubuntu user
keystone tenant-create --name ubuntu --description "Created by Juju"
keystone user-create --name ubuntu --tenant ubuntu --pass password --email juju@localhost
#keystone user-role-add --user ubuntu --role _member_ --tenant ubuntu

. ~/ubuntu-openrc

# create vm network
neutron net-create ubuntu-net
neutron subnet-create --name ubuntu-subnet --gateway 10.0.4.1 --dns-nameserver 10.0.3.1 ubuntu-net 10.0.4.0/24
neutron router-create ubuntu-router
neutron router-interface-add ubuntu-router ubuntu-subnet
neutron router-gateway-set ubuntu-router ext-net

# create pool of floating ips
i=0
while [ $i -ne 5 ]; do
	neutron floatingip-create ext-net
	i=$((i + 1))
done

# configure security groups
nova secgroup-add-rule default icmp -1 -1 0.0.0.0/0
nova secgroup-add-rule default tcp 22 22 0.0.0.0/0

# import key pair
nova keypair-add --pub-key id_rsa.pub ubuntu-keypair
