
.. code::

    usage: sudo openstack-install [-h] [-s] [-i] [-u] [-k] [-a ARCH] [-r RELEASE]
                                  [--with-maas-address IP]
                                  [--with-maas-apikey KEY] [-p]
    
    Ubuntu OpenStack Installer
    
    optional arguments:
      -h, --help            show this help message and exit
      -s, --enable-swift    Enable swift storage
      -i, --install-only    install and bootstrap MAAS/Juju/Landscape (as
                            applicable) only. Will not deploy any OpenStack
                            services in single or multi mode. You can invoke
                            openstack-status manually to continue.
      -u, --uninstall       Uninstalls the current cloud including removingof
                            packages.
      -k, --kill            Tear down existing cloud leaving userdata in place.
                            Useful for iterative deploys.
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


DESCRIPTION
===========

Ubuntu OpenStack Installer provides an extremely simple way to
install, deploy and scale an OpenStack cloud on top of Ubuntu server
and Juju. Deploy onto a single physical system using virtual machines
for testing, or use MAAS to deploy onto a cluster of any size.
