
.. code::

    cloud-install [-cish]

    Create an Ubuntu Openstack Cloud! (requires root privileges)

    Options:
      -c <file>   POSIX shell script to be sourced by installer
                  automating install by pre-setting menu responses.
      -s          enable swift-storage
      -i          install only (don't invoke cloud-status)
      -h          print this message



DESCRIPTION
===========

Ubuntu OpenStack Installer provides an extremely simple way to
install, deploy and scale an OpenStack cloud on top of Ubuntu server
and Juju. Deploy onto a single physical system using virtual machines
for testing, or use MAAS to deploy onto a cluster of any size.
