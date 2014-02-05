#
# Makefile for cloud-install
#
NAME = cloud-install-common
VERSION = $(shell echo `awk  -F "\"" '/^__version__="/{print $$2}' cloudinstall/__init__.py`)
TOPDIR = $(shell basename `pwd`)

$(NAME)_$(VERSION).orig.tar.gz: clean
	cd .. && tar czf $(NAME)_$(VERSION).orig.tar.gz $(TOPDIR) --exclude-vcs --exclude=debian

tarball: $(NAME)_$(VERSION).orig.tar.gz

clean:
	debian/rules clean

deb: clean tarball
	debuild -us -uc -i
