Using Juju in OpenStack
=======================

.. toctree::
   :maxdepth: 2

Once the OpenStack cloud has been deployed there are only a couple of steps
to enable juju to deploy charms into the private cloud.

.. attention::

    Juju requires swift storage so this needs to have been enabled
    during the install.

Generate necessary image metadata for Juju to utilize:

.. code::

    $ openstack-juju metadata generate-image -i <image_id> -s trusty

.. hint::

    <image_id> is found in the horizon dashboard `http://<public-ip>/horizon/project/images/`

    Alternatively, install **glance** client and retrieve the image list:

    .. code::

       $ sudo apt-get install glance
       $ source ~/.cloud-install/openstack-admin-rc
       $ glance image-list

       +--------------------------------------+---------------------------------------------------------------+-------------+------------------+-----------+--------+
       | ID                                   | Name                                                          | Disk Format | Container Format | Size      | Status |
       +--------------------------------------+---------------------------------------------------------------+-------------+------------------+-----------+--------+
       | 69dde281-db3c-4736-a5b4-a1999c201f58 | auto-sync/ubuntu-trusty-14.04-amd64-server-20141125-disk1.img | qcow2       | bare             | 255984128 | active |
       +--------------------------------------+---------------------------------------------------------------+-------------+------------------+-----------+--------+

Sync Juju tools and bootstrap onto your OpenStack private cloud:

.. code::

    $ openstack-juju sync-tools
    $ openstack-juju bootstrap --metadata-source /home/ubuntu

Now you can deploy charms within your OpenStack cloud.

.. code::

    $ openstack-juju deploy jenkins
    $ openstack-juju deploy -n 5 jenkins-slave
    $ openstack-juju add-relation jenkins jenkins-slave
    $ openstack-juju set jenkins password=AseCreTPassWoRd
    $ openstack-juju expose jenkins

.. caution::

    *Single Install Note* - Resources are limited in a single installation of OpenStack. So
    anything more than deploying a small service will fail due to resource constraints. For example,
    you could probably get away with deploying Wordpress and MySQL, but, not Hadoop or Jenkins.
