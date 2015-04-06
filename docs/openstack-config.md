# NAME

config.yaml - Ubuntu OpenStack Installer Configuration options

# SYNOPSIS

usage: sudo openstack-install -c config.yaml

# DESCRIPTION

Ubuntu OpenStack Installer configuration file

# OPTIONS

**debug**

    Enable debugging and provide a pdb post mortem shell if any exceptions arise.

**http_proxy**

    Enable HTTP proxy for Juju to utilize

**https_proxy**

    Enable HTTPS proxy for Juju to utilize

**apt_mirror**

    Alternate location of Ubuntu archives

**openstack_release**

    Set OpenStack release to be deployed, default: juno

**openstack_password**

    A password used throughout the OpenStack deployment

**headless**

    Do not use the GUI interface, default: false

**install_type**

    Type of installation, choices: Single, Multi, Landscape OpenStack Autopilot

**storage_backend**

    Type of storage to use, default: none, choices: ceph, swift, none

**upstream_deb**

    Provide an upstream openstack debian package, mostly used during development to
    quickly test changes in a Single installation.

**extra_ppa**

    Provide additional ppa's for the installer to look for when installing package
    dependencies.

# EXAMPLE

```
---
debug: false
headless: true
install_type: Single
openstack_password: passw0rd
```
