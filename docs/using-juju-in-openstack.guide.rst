Using Juju in OpenStack
=======================

Once the OpenStack cloud has been deployed there are only a couple of steps
to enable juju to deploy charms into the private cloud.

.. note::

    Juju requires swift storage so this needs to have been enabled
    during the install.

Bootstrap Juju
^^^^^^^^^^^^^^

Bootstrap Juju onto the new OpenStack deployment:

.. code::

    $ juju switch openstack
    $ juju metadata generate-image -i <image_id> -s trusty
    $ juju sync-tools
    $ juju bootstrap --metadata-source /home/ubuntu

Now you can deploy charms within your OpenStack cloud.

.. note::

    <image_id> is found in the horizon dashboard `http://<public-ip>/horizon/project/images/`
