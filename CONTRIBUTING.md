Guidelines to follow when writing new code or submitting patches.

# Filing a Bug
  1. Need output of *~/.cloud-install/commands.log*, use http://paste.ubuntu.com or some other form of pastebin.
  2. Which install type
  3. A `sosreport` from the host system if a *single* install, MAAS server if *multi/landscape autopilot* installation.

## Landscape OpenStack Autopilot requirements
  1. */var/log/landscape/job-handler-1.log*

      Obtain that by running the following from the MAAS system:
      ```
      $ JUJU_HOME=~/.cloud-install/juju juju ssh landscape/0
      $ sudo apt-get install pastebinit
      $ pastebinit /var/log/landscape/job-handler-1.log
      ```
      
  2. `lshw` output

     Obtain that by clicking on a node in the MAAS webui and following the link labeled `Show discovered details`
  3. Network response from Landscape's webui in the 'create-region' page.

     See: https://github.com/Ubuntu-Solutions-Engineering/openstack-installer/issues/374#issuecomment-71521918

# Filing a Pull Request
  1. Rebase from master before a PR
  2. Coherent subject/commit message
  3. (optional) dco
  4. Passes unittests, pep8, pyflakes (use `make tox` if installed.)


* Follow PEP-8 style guide.
  http://www.python.org/dev/peps/pep-0008/
* Coding guidelines based off with a few differences
  http://google-styleguide.googlecode.com/svn/trunk/pyguide.html
  - Documenting code differences
    We use the default sphinx style for documenting classes, functions, methods.
