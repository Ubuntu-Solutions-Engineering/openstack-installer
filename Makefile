#
# Makefile for cloud-installer
#
NAME = cloud-installer
VERSION = $(shell echo `awk  -F "\"" '/^__version__="/{print $$2}' cloudinstall/__init__.py`)

$(NAME)_$(VERSION).orig.tar.gz: clean
	cd .. && tar czf $(NAME)_$(VERSION).orig.tar.gz $(NAME) --exclude-vcs --exclude=debian

tarball: $(NAME)_$(VERSION).orig.tar.gz

clean:
	debian/rules clean

deb:
	debuild -us -uc -i
