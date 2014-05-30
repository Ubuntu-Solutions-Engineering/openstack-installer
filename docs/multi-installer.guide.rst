Multi Installer Guide
=====================

Pre-requisites
^^^^^^^^^^^^^^

Add the `cloud-installer` ppa to your system.

.. code::

   $ sudo apt-add-repository ppa:cloud-installer/ppa

.. note::

   Adding the ppa is only necessary until an official release to the
   archives has been announced.

Installation
^^^^^^^^^^^^

Install the cloud-installer via `apt-get`

.. code::

   $ sudo apt-get install cloud-installer

Start the installation
^^^^^^^^^^^^^^^^^^^^^^

To start the installation run the following command

.. code::

   $ sudo cloud-install

An initial dialog box will appear asking you to select which type of
install, choose **Multi-system**.

Setting a password
^^^^^^^^^^^^^^^^^^

When asked to set the openstack password it should be noted that this password is
used throughout all openstack related services (ie Horizon login password). The only
service that does not use this password is **juju-gui**.

Next Steps
^^^^^^^^^^

The installer will run through a series of steps starting with making
sure the necessary bits are available for a multi system installation
and ending with a `juju` bootstrapped system.

.. todo::

   Finish this guide.
