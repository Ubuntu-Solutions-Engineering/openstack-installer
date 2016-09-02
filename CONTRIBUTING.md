Guidelines to follow when writing new code or submitting patches.

# Filing a Bug
  1. Need output of *~/.cloud-install/commands.log*, use http://paste.ubuntu.com or some other form of pastebin.
  2. Autopilot installation is the only method supported, all other installation types will be closed as invalid.

## Autopilot requirements
  1. */var/log/landscape-server/job-handler.log*

      Obtain that by running the following from the MAAS system:
      ```
      $ JUJU_HOME=~/.cloud-install/juju juju ssh landscape/0
      $ sudo apt-get install pastebinit
      $ pastebinit /var/log/landscape-server/job-handler.log
      ```
      
  2. `lshw` output

     Obtain that by clicking on a node in the MAAS webui and following the link labeled `Show discovered details`
  3. Network response from Landscape's webui in the 'create-region' page.

     See: https://github.com/Ubuntu-Solutions-Engineering/openstack-installer/issues/374#issuecomment-71521918

# Filing a Pull Request
We are not accepting any new contributions as this installer is in a limited supported maintenance mode.
