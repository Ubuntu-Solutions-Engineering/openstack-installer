Using Juju in Openstack
=======================

Once the Openstack cloud has been deployed there are only a couple of steps
to enable juju to deploy charms into the private cloud.

Update ~/.juju/environments.yaml
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the users **~/.juju/environments.yaml** file there is a a **openstack**
stanza.

.. code::

    openstack:
      type: openstack
      use-floating-ip: true
      use-default-secgroup: true
      network: ubuntu-net
      auth-url: http://keystoneurl:5000/v2.0/
      tenant-name: ubuntu
      region: RegionOne
      auth-mode: userpass
      username: ubuntu
      password: pass

The credentials are already filled out for you, however, you'll need to set the
**auth-url** to your Keystone public address.

Bootstrap Juju
^^^^^^^^^^^^^^

Once the environments are updated simple run:

.. code::

    $ juju switch openstack
    $ juju bootstrap

Now you can deploy charms within your Openstack cloud.
