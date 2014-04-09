Single Installer Guide
===============

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
install, choose **Single system**.

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
