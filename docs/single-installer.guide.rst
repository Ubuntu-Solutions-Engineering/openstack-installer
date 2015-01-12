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

.. important::

    The installer should be run with sudo.

Optional Flags

.. code::

    usage: openstack-install [-h] [-i] [-u] [-k]
                             [--openstack-release OPENSTACK_RELEASE] [-a ARCH]
                             [-r RELEASE] [--with-maas-address IP]
                             [--with-maas-apikey KEY] [-p]
                             [--extra-ppa EXTRA_PPA [EXTRA_PPA ...]]
                             [--upstream-deb UPSTREAM_DEB] [--version]
    
    Ubuntu Openstack Installer
    
    optional arguments:
      -h, --help            show this help message and exit
      -i, --install-only    install and bootstrap MAAS/Juju/Landscape (as
                            applicable) only. Will not deploy any OpenStack
                            services in single or multi mode. You can invoke
                            openstack-status manually to continue.
      -u, --uninstall       Uninstalls the current cloud including removing of
                            packages.
      -k, --kill            Tear down existing cloud leaving userdata in place.
                            Useful for iterative deploys.
      --openstack-release OPENSTACK_RELEASE
                            Specify a specific OpenStack release by code-name,
                            e.g. 'icehouse' or 'juno'
      -a ARCH               <arch, ..> comma-separated list of architectures to
                            filter available cloud images with which to populate
                            Glance, e.g. amd64,arm64
      -r RELEASE            <rel, ..> comma-separated list of Ubuntu releases to
                            filter available cloud images with which to populate
                            Glance, e.g. precise,trusty
      --with-maas-address IP
                            Specify an existing MAAS ip address
      --with-maas-apikey KEY
                            Specify a MAAS admin user apikey
      -p, --placement       Show machine placement UI before deploying
      --extra-ppa EXTRA_PPA [EXTRA_PPA ...]
                            Append additional ppas to the single installers cloud-
                            init configuration.
      --upstream-deb UPSTREAM_DEB
                            Upload a local copy of openstack debian package to be
                            used in a single install. (DEVELOPERS)
      --version             show program's version number and exit

.. attention::

    Enabling swift storage requires at least 3 instances and another additional
    instance for swift-proxy.

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

Accessing the OpenStack environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

See :doc:`Using Juju in OpenStack Guide <using-juju-in-openstack.guide>`

Troubleshooting
^^^^^^^^^^^^^^^

The installer keeps its own logs in **$HOME/.cloud-install/commands.log**.

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

Advanced Usage
^^^^^^^^^^^^^^

It is possible to stop and start the container housing OpenStack.
To do so run the following from the container host:

.. code::

   $ sudo lxc-stop -n uoi-bootstrap
   $ sudo lxc-start -n uoi-bootstrap -d
   $ ssh ubuntu@ip-of-uoi-bootstrap-container
   (uoi-bootstrap) $ JUJU_HOME=~/.cloud-install juju status

From this point on it is a matter of waiting for all services to be restarted
and shown as **agent-state: started** within the `juju status` output.

Once the services are started again, running the following from the host
system will bring up the status screen again:

.. code::

   $ openstack-status

.. caution::

   Depending on the host system, times vary when starting up all the services
   to when the cloud is accessible again. Most test runs of this have taken
   roughly 30 minutes to come back online.

   Disclaimer: As the single installer is provided as a demo or proof-of-concept,
   support for this advanced usage is very minimal.
