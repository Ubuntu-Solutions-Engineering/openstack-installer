#!/bin/bash -ex

sudo add-apt-repository -y ppa:ubuntu-lxc/lxd-stable
sudo apt-get update
sudo apt-get install -qyf lxd
sudo su ubuntu -c "lxc list"
sudo su ubuntu -c "lxd-images import ubuntu --alias ubuntu"

OSI_TESTRUNNER_ID=battlemidgetjenkins sudo -E openstack-install -c $OPENSTACK_CONFIG
