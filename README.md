# Ubuntu Cloud Installer

## Developers

### Pre-reqs

* debhelper
* dh-python
* python3-all
* python3-mock
* python3-nose
* python3-oauthlib
* python3-passlib
* python3-requests
* python3-requests-oauthlib
* python3-setuptools
* python3-urwid
* python3-ws4py
* python3-yaml

### Running tests

`$ nosetests3 test`

### Building a package

`$ make deb`

This will build a package for the current host system. If you wish to
build for other releases please checkout
[sbuild](https://wiki.ubuntu.com/SimpleSbuild)

### Building the tarball only

`$ make tarball`

### Cleaning

`$ make clean`

## Installing

### PPA

`$ sudo apt-add-repository ppa:cloud-installer/ppa`

### Running

`$ sudo cloud-install`

# Copyright

Copyright 2014 Canonical, Ltd.

# License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.
