Developer Guide
===============

The document walks you through installing the necessary packages and
environment preparations in order to build the cloud installer.

There is also auto-generated :doc:`API Documentation <modules>` available.

Base system
^^^^^^^^^^^

Development and testing is done on Ubuntu and using a release of
**Trusty** or later.


Building cloud installer
^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   Although not required, **Sbuild** is the preferred way for building the package set. Please
   refer to this `wiki page <https://wiki.ubuntu.com/SimpleSbuild>`_ on
   setting up sbuild.

   Just like the base system the sbuild chroots need to be `Trusty` or
   later, but the architecture of the chroots does not matter.

Once **sbuild** is configured, checkout the source code of the
installer:

.. code::

   $ git clone https://github.com/Ubuntu-Solutions-Engineering/openstack-installer.git ~/openstack-installer
   $ cd ~/openstack-installer
   $ git submodule init
   $ git submodule update

Use the target 'install-dependencies' to install a custom binary package for the build dependencies:

.. code::

   $ make install-dependencies

From here you can build the entire package set by running:

.. code::

   $ make sbuild
   # or, if you prefer not to use sbuild:
   $ make deb
   # or a source only package
   $ make deb-src

Once finished your packages will be stored in the top level directory
where your OpenStack project is kept.

.. code::

   $ ls ../*.deb

Running the OpenStack installer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Running the installer for testing currently requires installing the packages. (Unit tests can be run without installing the packages, provided the `install-dependencies` make target has been run.)

.. warning::
   Running the installer as below will install MAAS on your development system.
   This will create a 'maas' user and add a database to your local postgres instance.
   It will also configure bind9 DNS and a DHCP server for use with MAAS, although MAAS
   should not activate those by default. If any of this is not desirable, you will need
   to find a different machine to develop on.

After building the packages using either 'make deb' or 'make sbuild', you can install and run with the 'run' target:

.. code::

   $ sudo make run type=single
   # or
   $ sudo make run type=multi

You can also set the MAAS_HTTP_PROXY env var for the openstack-install command like this:

.. code::

   $ sudo make run type=single proxy=http://myproxy/

If you are running the landscape installer, you will want to use the 'landscape' target:

.. code::

   $ sudo make landscape proxy=http://myproxy/

Running the OpenStack status screen
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have run the installer and are working on changes to the status screen (in cloudinstall/), you can re-run the status screen with the correct python path using this target:

.. code::

   $ make status

If you are testing the status screen's code for deploying charms, you may need to first start your juju environment over from scratch:

.. code::

    $ juju destroy-environment local
    $ juju bootstrap
    $ make status

Changing the log level
^^^^^^^^^^^^^^^^^^^^^^

The openstack-status program logs to ~/.cloud-install/commands.log. The
default log level for that log is "DEBUG". Most of the program logs at
the DEBUG level, which is the most verbose that is currently defined.
If you want a different log level, you can set the UCI_LOGLEVEL
environment variable. Your choices are "DEBUG", "INFO", "WARNING",
"ERROR", and "CRITICAL".

.. code::

    $ UCI_LOGLEVEL=ERROR openstack-status


Building documentation
^^^^^^^^^^^^^^^^^^^^^^

Documentation will be built in **docs/_build/html**, and requires **Sphinx** to build.

.. code::

   $ cd docs && make html


Running Tests
^^^^^^^^^^^^^

A unit test suite is in tests/ and is run using Nose_ and tox_.
Tox will cover both pep8 and flakes automatically and unit tests
do not require a live Juju or MAAS connection.

Run it as follows:

.. code::

   $ make test

.. _Nose: https://nose.readthedocs.org/en/latest/
.. _tox: https://testrun.org/tox/latest/

