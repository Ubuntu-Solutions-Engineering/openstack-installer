# Ubuntu Cloud Installer

## Developers

### Pre-reqs

* python3-yaml
* python3-urwid
* python3-nose
* python3-mock
* python3-oauthlib
* python3-passlib
* python3-requests
* python3-requests-oauthlib
* python3-setuptools
* python3-all
* debhelper
* po-debconf
* dh-python

### Running tests

`$ nosetests3 test`

### Building a package

`$ make deb`

### Building the tarball only

`$ make tarball`

### Cleaning

`$ make clean`

## Users

The packages are in process of being included in the archive. Currently, the packages need to be built
manually as described above. Once built you will have the option to install **cloud-install-{multi,single,landscape}**. Once those packages are installed the following command will start the installer:

`$ sudo cloud-install`
