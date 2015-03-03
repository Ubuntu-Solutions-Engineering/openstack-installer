sudo make deb
sudo dpkg -i ../openstack_*.deb
sudo python3 setup.py build
sudo python3 setup.py install
