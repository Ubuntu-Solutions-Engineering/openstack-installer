NAME
====

openstack-juju - Ubuntu OpenStack Installer documentation

SYNOPSIS
========

usage: openstack-juju [subcommand] [opts]

$ openstack-juju deploy jenkins
$ openstack-juju deploy -n 5 jenkins-slave
$ openstack-juju add-relation jenkins jenkins-slave
$ openstack-juju set jenkins password=AseCreTPassWoRd
$ openstack-juju expose jenkins

DESCRIPTION
===========

This is a wrapper around Juju to setup necessary requirements for allowing
a user to orchestrate services on top of OpenStack.
