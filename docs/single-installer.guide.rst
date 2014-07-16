Single Installer Guide
======================

Pre-requisites
^^^^^^^^^^^^^^

Add the `cloud-installer` ppa to your system.

.. code::

   $ sudo apt-add-repository ppa:juju/stable
   $ sudo apt-add-repository ppa:cloud-installer/ppa
   $ sudo apt-get update

.. note::

   Adding the ppa is only necessary until an official release to the
   archives has been announced.

Recommended Hardware
^^^^^^^^^^^^^^^^^^^^

The installer would work best with at least:

- 12G RAM
- 100G HDD (SSD for optimal performance)
- 8 CPUS

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

.. note::

    The installer should be run as a non-root user.

Optional Flags

.. code::

    Options:
      -c <file>   POSIX shell script to be sourced by installer
                  automating install by pre-setting menu responses.
      -s          enable swift-storage
      -i          install only (don't invoke cloud-status)
      -u          uninstall the cloud
      -h          print this message


.. note::

    Enabling swift storage requires at least 3 instances and another additional
    instance for swift-proxy.

An initial dialog box will appear asking you to select which type of
install, choose **Single system**.

Setting a password
^^^^^^^^^^^^^^^^^^

When asked to set the openstack password it should be noted that this password
is used throughout all openstack related services (ie Horizon login password).
The only service that does not use this password is **juju-gui**.

Next Steps
^^^^^^^^^^

The installer will run through a series of steps starting with making
sure the necessary bits are available for a single system installation
and ending with a `juju` bootstrapped system.

When the bootstrapping has finished it will immediately load the
status screen. From there you can see the nodes listed along with the
deployed charms necessary to start your private openstack cloud.

Adding additional compute nodes, block storage, object storage, and
controllers can be done by pressing `F6` and making the selection on
the dialog box.

Finally, once those nodes are displayed and the charms deployed the
horizon dashboard will be available to you for managing your openstack
cloud.

Troubleshooting
^^^^^^^^^^^^^^^

The installer keeps its own logs in **$HOME/.cloud-install/commands.log**.

Uninstalling
^^^^^^^^^^^^

To uninstall and cleanup your system run the following

.. code::

    $ sudo cloud-install -u single-system
