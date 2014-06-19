#!/bin/sh -e

. ~/admin-openrc

wget http://cloud-images.ubuntu.com/trusty/current/MD5SUMS

wget http://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img
glance image-create --name ubuntu-trusty-daily --disk-format qcow2 --container-format bare --owner admin --file trusty-server-cloudimg-amd64-disk1.img --checksum $(grep trusty-server-cloudimg-amd64-disk1.img MD5SUMS | cut -d " " -f 1) --is-public True
