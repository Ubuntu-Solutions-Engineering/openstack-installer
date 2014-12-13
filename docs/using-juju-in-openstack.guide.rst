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

    $ openstack-juju metadata generate-image -i <image_id> -s trusty
    $ openstack-juju sync-tools
    $ openstack-juju bootstrap --metadata-source /home/ubuntu

.. note::

    <image_id> is found in the horizon dashboard `http://<public-ip>/horizon/project/images/`

Now you can deploy charms within your OpenStack cloud.

.. code::

    $ openstack-juju deploy jenkins
    $ openstack-juju deploy -n 5 jenkins-slave
    $ openstack-juju add-relation jenkins jenkins-slave
    $ openstack-juju set jenkins password=AseCreTPassWoRd
    $ openstack-juju expose jenkins

.. note::

    *Single Install Note* - Resources are limited in a single installation of OpenStack. So
    anything more than deploying a small service will fail due to resource constraints. For example,
    you could probably get away with deploying Wordpress and MySQL, but, not Hadoop or Jenkins.
