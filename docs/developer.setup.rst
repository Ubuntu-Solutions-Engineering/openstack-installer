Developer Guide - Setup
=======================

The document walks you through installing the necessary packages and
environment preparations in order to build the cloud installer.

Base system
^^^^^^^^^^^

Development and testing is done on Ubuntu and using a release of
**Trusty** or later.

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
