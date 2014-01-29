#!/bin/bash

cat > /tmp/kill_it_with_fire <<EOF
from django.contrib.auth.models import User
u = User.objects.get(username='root')
u.delete()
u.delete()
EOF
echo


cat /tmp/kill_it_with_fire | sudo maas shell

rm -rf ~/.ssh
rm -rf ~/.juju

sudo apt-get -yy remove maas* maas-* juju* juju-*
sudo apt-get -yy purge maas* maas-* juju* juju-*
sudo service apache2 stop
