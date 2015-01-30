Deployment Test Guide
=====================

The document walks you through doing headless installs and using our testing
tools to verify our installer is in top notch shape.

Base system
^^^^^^^^^^^

Testing is done on Ubuntu and using a release of **Trusty** or later.


Install OpenStack Installer from the PPA
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

   We test all branches which are **master, testing, and stable**, but helping
   to keep our master branch green is a huge help.

First, the ppas:

.. code::

   $ sudo apt-add-repository ppa:juju/stable
   $ sudo apt-add-repository ppa:maas-maintainers/stable
   $ sudo apt-add-repository ppa:cloud-installer/experimental
   $ sudo apt-get update

Next, needed packages:

.. code::

   $ sudo apt-get install openstack openstack-ci git

Now, grab the tests:

.. code::

   $ git clone https://github.com/Ubuntu-Solutions-Engineering/openstack-tests.git ~/openstack-tests
   $ cd ~/openstack-tests

All tests are kept in **quality** and **regressions** sub-folders.

Testing the single install path
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A sample configuration file to use with the Single install path, save this as **config-single.yaml**:

.. code::

   headless: true
   install_type: Single
   openstack_password: pass

We're ready to start our tests:

.. code::

   $ sudo openstack-ci -c ../config-single.yaml --with-install -a

This command will push our single path install through the tester and perform all related single path install tests.

Testing the multi install path
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A sample configuration file for Multi install path, save this as **config-multi.yaml**:

.. code::

    headless: true
    install_type: Multi
    maascreds:
      api_host: 172.16.0.1
      api_key: y55mPM2zBzE5wsR9CF:pk7PQ563tZ6AupgZ2y:vMk3qFLuANBJ8dZ6yqHnU8yuMF883HXW
    openstack_password: pass
    placements:
      /MAAS/api/1.0/nodes/node-24ac63e0-a122-11e4-b67e-a0cec8006f97/:
        assignments:
          KVM:
          - nova-compute
          - quantum-gateway
          LXC:
          - nova-cloud-controller
          - glance
          - glance-simplestreams-sync
          - openstack-dashboard
          - keystone
          - mysql
          - rabbitmq-server
        constraints: {}

.. attention::

   The **placements** directive is obtained by pulling the node id of a machine you wish to deploy the cloud
   to. In the above example there is 1 machine in the MAAS with an id of `node-24ac63e0-a122-11e4-b67e-a0cec8006f97`.
   We're telling the installer that we should place nova-compute, quantum-gateway on separate KVM's within that
   system and the rest of the OpenStack services within LXC's also within that same system.

   This placements directive is required for a complete unattended installation of OpenStack within MAAS.

Run the tests:

.. code::

   $ JUJU_BOOTSTRAP_TO=juju-bootstrap-node-1.maas openstack-ci -c ../config-multi.yaml --with-install -a

.. attention::

   **JUJU_BOOTSTRAP_TO** is not the same node as the one in the placements file. `juju-bootstrap-node-1.maas`
   is a second system in MAAS that Juju will bootstrap itself to.

Testing the Landscape OpenStack Autopilot path
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A sample Landscape OpenStack Autopilot config, save this as **config-landscape.yaml**:

.. code::

    headless: true
    install_type: Landscape OpenStack Autopilot
    landscapecreds:
      admin_email: foo@bar.com
      admin_name: foo ey bar
      maas_apikey: y55mPM2zBzE5wsR9CF:pk7PQ563tZ6AupgZ2y:vMk3qFLuANBJ8dZ6yqHnU8yuMF883HXW
      maas_server: 172.16.0.1
      system_email: ayo@foo.bar.com
    maascreds:
      api_host: 172.16.0.1
      api_key: y55mPM2zBzE5wsR9CF:pk7PQ563tZ6AupgZ2y:vMk3qFLuANBJ8dZ6yqHnU8yuMF883HXW
    openstack_password: pass

Run the tests:

.. code::

   $ JUJU_BOOTSTRAP_TO=juju-bootstrap-node-1.maas openstack-ci -c ../config-landscape.yaml --with-install -a

Performing a specific Test
^^^^^^^^^^^^^^^^^^^^^^^^^^

Referring to the same identifier name as stated in the **Reports** section running a single test without
performing an install can be run like:

.. code::

   $ openstack-ci -c ../config-landscape.yaml -t 00_autopilot_deployed

This would refer to the `00_autopilot_deployed.py` file under the `quality` directory.

Reports
^^^^^^^

Testing reports are kept in `~/.cloud-install/reports`, they are prefixed by the identifer of the particular
test that generated the report and a current timestamp. All tests are keyed by the filename of the tests minus
`.py`. For example, the test **quality/00_multi_deployed.py** will have an indentifier of `00_multi_deployed`.


Example output
^^^^^^^^^^^^^^

Example output of a Multi install test:

.. code::

    adam@maas:~/openstack-tests$ JUJU_BOOTSTRAP_TO=authorized-seat.maas openstack-ci -c ../config-multi.yaml --with-install -a
    [INFO  • 15:49:24 • openstackci] Initializing tests.
    [INFO  • 15:49:24 • openstackci] Deploying environment.
    [INFO  • 01-29 15:49:25 • cloudinstall.install] Running in headless mode.
    [INFO  • 01-29 15:49:25 • cloudinstall.install] Performing a Multi install with existing MAAS
    [INFO  • 01-29 15:49:25 • cloudinstall.task] [TASKLIST] ['Bootstrapping Juju']
    [INFO  • 01-29 15:49:25 • cloudinstall.task] [TASK] Bootstrapping Juju
    [INFO  • 01-29 15:49:25 • cloudinstall.consoleui] Bootstrapping Juju
    [INFO  • 01-29 15:54:24 • cloudinstall.core] Running openstack-status in headless mode.
    [INFO  • 01-29 15:54:24 • cloudinstall.consoleui] Loaded placements from file.
    [INFO  • 01-29 15:54:25 • cloudinstall.consoleui] Waiting for 1 maas machines to be ready. Machines Summary: 1 deployed, 5 ready
    [INFO  • 01-29 15:54:26 • cloudinstall.consoleui] Waiting for machines to start: 1 unknown
    [INFO  • 01-29 15:54:38 • cloudinstall.consoleui] Waiting for machines to start: 1 pending
    [INFO  • 01-29 15:59:35 • cloudinstall.consoleui] Waiting for machines to start: 1 down (started)
    [INFO  • 01-29 15:59:56 • cloudinstall.consoleui] Verifying service deployments
    [INFO  • 01-29 15:59:56 • cloudinstall.consoleui] Missing ConsoleUI() attribute: set_pending_deploys
    [INFO  • 01-29 15:59:56 • cloudinstall.consoleui] Checking if MySQL is deployed
    [INFO  • 01-29 15:59:56 • cloudinstall.consoleui] Deploying MySQL to machine lxc:1
    [INFO  • 01-29 16:00:03 • cloudinstall.consoleui] Deployed MySQL.
    [INFO  • 01-29 16:00:03 • cloudinstall.consoleui] Checking if Keystone is deployed
    [INFO  • 01-29 16:00:03 • cloudinstall.consoleui] Deploying Keystone to machine lxc:1
    [WARNING • 01-29 16:03:00 • cloudinstall.core] deferred deploying to these machines: [<MaasMachine(dismal-flight.maas,None,8.0G,111.79G,4)>]
    [INFO  • 01-29 16:03:00 • cloudinstall.consoleui] Keystone is waiting for another service, will re-try in a few seconds
    [INFO  • 01-29 16:03:05 • cloudinstall.consoleui] Checking if Keystone is deployed
    [INFO  • 01-29 16:03:05 • cloudinstall.consoleui] Deploying Keystone to machine lxc:1
    [INFO  • 01-29 16:03:05 • cloudinstall.consoleui] Checking availability of mysql: started
    [INFO  • 01-29 16:03:12 • cloudinstall.consoleui] Deployed Keystone.
    [INFO  • 01-29 16:03:12 • cloudinstall.consoleui] Checking if Compute is deployed
    [INFO  • 01-29 16:03:12 • cloudinstall.consoleui] Deploying Compute to machine kvm:1
    [INFO  • 01-29 16:03:19 • cloudinstall.consoleui] Deployed Compute.
    [INFO  • 01-29 16:03:19 • cloudinstall.consoleui] Checking if Controller is deployed
    [INFO  • 01-29 16:03:19 • cloudinstall.consoleui] Deploying Controller to machine lxc:1
    [INFO  • 01-29 16:03:26 • cloudinstall.consoleui] Deployed Controller.
    [INFO  • 01-29 16:03:26 • cloudinstall.consoleui] Checking if Glance is deployed
    [INFO  • 01-29 16:03:27 • cloudinstall.consoleui] Deploying Glance to machine lxc:1
    [INFO  • 01-29 16:03:33 • cloudinstall.consoleui] Deployed Glance.
    [INFO  • 01-29 16:03:33 • cloudinstall.consoleui] Checking if Glance - Simplestreams Image Sync is deployed
    [INFO  • 01-29 16:03:33 • cloudinstall.consoleui] Deploying Glance - Simplestreams Image Sync to machine lxc:1
    [INFO  • 01-29 16:03:39 • cloudinstall.consoleui] Checking if Openstack Dashboard is deployed
    [INFO  • 01-29 16:03:40 • cloudinstall.consoleui] Deploying Openstack Dashboard to machine lxc:1
    [INFO  • 01-29 16:03:46 • cloudinstall.consoleui] Deployed Openstack Dashboard.
    [INFO  • 01-29 16:03:46 • cloudinstall.consoleui] Checking if Neutron is deployed
    [INFO  • 01-29 16:03:46 • cloudinstall.consoleui] Deploying Neutron to machine kvm:1
    [INFO  • 01-29 16:03:53 • cloudinstall.consoleui] Deployed Neutron.
    [INFO  • 01-29 16:03:53 • cloudinstall.consoleui] Checking if RabbitMQ Server is deployed
    [INFO  • 01-29 16:03:54 • cloudinstall.consoleui] Deploying RabbitMQ Server to machine lxc:1
    [INFO  • 01-29 16:04:00 • cloudinstall.consoleui] Deployed RabbitMQ Server.
    [INFO  • 01-29 16:04:20 • cloudinstall.consoleui] Checking availability of nova-cloud-controller: pending
    [INFO  • 01-29 16:05:42 • cloudinstall.consoleui] Checking availability of nova-cloud-controller: pending
    [INFO  • 01-29 16:06:53 • cloudinstall.consoleui] Checking availability of nova-cloud-controller: pending
    [INFO  • 01-29 16:08:05 • cloudinstall.consoleui] Checking availability of nova-cloud-controller: pending
    [INFO  • 01-29 16:08:57 • cloudinstall.consoleui] Checking availability of nova-cloud-controller: pending
    [INFO  • 01-29 16:09:27 • cloudinstall.consoleui] Checking availability of nova-cloud-controller: installed
    [INFO  • 01-29 16:09:59 • cloudinstall.consoleui] Checking availability of nova-cloud-controller: started
    [INFO  • 01-29 16:13:25 • cloudinstall.consoleui] Checking availability of keystone: started
    [INFO  • 01-29 16:13:45 • cloudinstall.consoleui] Checking availability of keystone: started
    [INFO  • 01-29 16:13:45 • cloudinstall.consoleui] Checking availability of nova-cloud-controller: started
    [INFO  • 01-29 16:14:48 • cloudinstall.consoleui] Checking availability of quantum-gateway: started
    [INFO  • 01-29 16:14:48 • cloudinstall.consoleui] Validating network parameters for Neutron
    [INFO  • 01-29 16:14:59 • cloudinstall.consoleui] All systems go!
    [INFO  • 01-29 16:15:19 • cloudinstall.core] All services deployed, relations set, and started
    [INFO  • 01-29 16:15:19 • cloudinstall.utils] Cleanup, saving latest config object.
    [INFO  • 16:15:19 • openstackci] Authenticated against juju
    [INFO  • 16:15:19 • openstackci] Test: Verifies the multi install deployed.
    [INFO  • 16:15:20 • openstackci] Checking mysql/0
    [INFO  • 16:15:20 • openstackci] Checking nova-compute/0
    [INFO  • 16:15:20 • openstackci] Checking keystone/0
    [INFO  • 16:15:20 • openstackci] Checking nova-cloud-controller/0
    [INFO  • 16:15:20 • openstackci] Checking openstack-dashboard/0
    [INFO  • 16:15:20 • openstackci] Checking glance-simplestreams-sync/0
    [INFO  • 16:15:20 • openstackci] Checking glance/0
    [INFO  • 16:15:20 • openstackci] Checking quantum-gateway/0
    [INFO  • 16:15:20 • openstackci] Checking rabbitmq-server/0
    [INFO  • 16:15:20 • openstackci] Result: [PASS] Test services started ['mysql/0', 'nova-compute/0', 'keystone/0', 'nova-cloud-controller/0', 'openstack-dashboard/0', 'glance-simplestreams-sync/0', 'glance/0', 'quantum-gateway/0', 'rabbitmq-server/0']
    [INFO  • 16:15:20 • openstackci] Report saved: /home/adam/.cloud-install/reports/00_multi_deployed_2015-01-29T16:15:19.386972.yaml
    [INFO  • 16:15:20 • openstackci] Test run complete.

An example of the report:

.. code::

    adam@maas:~/openstack-tests$ cat ../.cloud-install/reports/00_multi_deployed_2015-01-29T16\:15\:19.386972.yaml 
    description: Verifies the multi install deployed.
    failed:
      tests_ran: []
      total: 0
    name: Multi install deploy
    status:
      code: 0
      text: Passed
    success:
      tests_ran:
      - Test services started ['mysql/0', 'nova-compute/0', 'keystone/0', 'nova-cloud-controller/0',
        'openstack-dashboard/0', 'glance-simplestreams-sync/0', 'glance/0', 'quantum-gateway/0',
        'rabbitmq-server/0']
      total: 1
    timestamp: '2015-01-29T16:15:19.386972'
