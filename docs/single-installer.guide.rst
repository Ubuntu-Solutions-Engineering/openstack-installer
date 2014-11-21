Single Installer Guide
======================

Pre-requisites
^^^^^^^^^^^^^^

Add the OpenStack installer ppa to your system.

.. code::

   $ sudo apt-add-repository ppa:cloud-installer/testing
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

Install the OpenStack installer via `apt-get`

.. code::

   $ sudo apt-get install openstack

Start the installation
^^^^^^^^^^^^^^^^^^^^^^

To start the installation run the following command

.. code::

   $ sudo openstack-install

.. note::

    The installer should be run as a non-root user.

Optional Flags

.. code::

    Options:
      -c <file>   POSIX shell script to be sourced by installer
                  automating install by pre-setting menu responses.
      -s          enable swift-storage
      -i          install only (don't invoke openstack-status)
      -u          uninstall the cloud
      -h          print this message


.. note::

    Enabling swift storage requires at least 3 instances and another additional
    instance for swift-proxy.

.. note::

    If you wish to deploy services to this OpenStack using juju you will need
    to enable swift storage.

An initial dialog box will appear asking you to select which type of
install, choose **Single system**.

Setting a password
^^^^^^^^^^^^^^^^^^

When asked to set the OpenStack password it should be noted that this password
is used throughout all OpenStack related services (ie Horizon login password).

Installing of Services
^^^^^^^^^^^^^^^^^^^^^^

The installer will run through a series of steps starting with making
sure the necessary bits are available for a single system installation
and ending with a `juju` bootstrapped system.

When the bootstrapping has finished it will immediately load the
status screen. From there you can see the nodes listed along with the
deployed charms necessary to start your private OpenStack cloud.

Adding additional compute nodes, block storage, object storage, and
controllers can be done by pressing `A` and making the selection on
the dialog box.

Finally, once those nodes are displayed and the charms deployed the
horizon dashboard will be available to you for managing your OpenStack
cloud.

Logging into Horizon (Openstack Dashboard)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The login credentials for the dashboard are:

* username: **ubuntu**
* password: **"password that was set during installation"**

Accessing the Juju environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Since the entire installation is contained within an lxc container an
additional step is required to access the juju environment.

To find out the ip address of the container housing the environment run:

.. code::

   $ sudo lxc-ls -f uoi-bootstrap

   NAME           STATE    IPV4                      IPV6  AUTOSTART
   -----------------------------------------------------------------
   uoi-bootstrap  RUNNING  10.0.3.19, 192.168.122.1  -     NO       

From here you can ssh into the container:

.. code::

   $ ssh ubuntu@10.0.3.19


.. note::

   By default the ssh key from the host system will already be available within the
   container. If the installer generated an ssh-key that key will be passwordless,
   however, if an existing ssh key was found it will use that instead.

Once in the container simply use juju as normal:

.. code::

   ubuntu@uoi-bootstrap $ juju status
   ubuntu@uoi-bootstrap $ juju deploy <service>


Troubleshooting
^^^^^^^^^^^^^^^

The installer keeps its own logs in **$HOME/.cloud-install/commands.log** within the
container.

Killing the current OpenStack deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because the entire installation is within a single container it is easy to start a new
deployment without uninstalling everything beforehand. To do that run:

.. code::

   $ sudo openstack-install -k

This will stop and destroy the container housing the OpenStack installation and allow you
to start over.

Uninstalling
^^^^^^^^^^^^

To uninstall and cleanup your system run the following

.. code::

    $ sudo openstack-install -u
