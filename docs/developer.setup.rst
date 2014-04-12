Developer Guide - Setup
=======================

The document walks you through installing the necessary packages and
environment preparations in order to build the cloud installer.

Base system
^^^^^^^^^^^

Development and testing is done on Ubuntu and using a release of
**Trusty** or later.

Needed packages
^^^^^^^^^^^^^^^

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


Building cloud installer
^^^^^^^^^^^^^^^^^^^^^^^^

**Sbuild** is the preferred way for building the package set. Please
refer to this `wiki page <https://wiki.ubuntu.com/SimpleSbuild>`_ on
setting up sbuild.

Just like the base system the sbuild chroots need to be `Trusty` or
later.

.. note::

   The architecture of the chroots do not matter.

Once **sbuild** is configured, checkout the source code of the
installer

.. code::

   $ git clone https://github.com/Ubuntu-Solutions-Engineering/cloud-installer.git ~/cloud-installer
   $ cd cloud-installer

From here you can build the entire package set by running:

.. code::

   $ make sbuild

Once finished your packages will be stored in the top level directory
where your cloud-installer project is kept.

.. code::

   $ ls ../*.deb

Building documentation
^^^^^^^^^^^^^^^^^^^^^^

Documentation will be built in **docs/_build/html**, and requires **Sphinx** to build.

.. code::

   $ cd docs && make html


Running Tests
^^^^^^^^^^^^^

Tests can be ran against a set of exported data(**default**) or a live machine. In
order to test against live data the following environment variable is
used.


.. code::

   $ JUJU_LIVE=1 nosetests3 test
