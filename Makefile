#
# Makefile for cloud-install
#
NAME = cloud-installer
GIT_REV = $(shell git log --oneline -n1| cut -d" " -f1)
VERSION = $(shell echo `awk  -F "\"" '/^__version__ = "/{print $$2}' cloudinstall/__init__.py`)+git-${GIT_REV}
TOPDIR = $(shell basename `pwd`)

$(NAME)_$(VERSION).orig.tar.gz: clean
	cd .. && tar czf $(NAME)_$(VERSION).orig.tar.gz $(TOPDIR) --exclude-vcs --exclude=debian

tarball: $(NAME)_$(VERSION).orig.tar.gz

clean:
	@debian/rules clean
	@rm -rf debian/cloud-install

deb-src: clean tarball
	wrap-and-sort
	@debuild -S -us -uc

deb: clean tarball
	wrap-and-sort
	@debuild -us -uc -i

current_version:
	@echo ${GIT_REV}

status:
	PYTHONPATH=$(shell pwd):$(PYTHONPATH) bin/cloud-status

.PHONY: status current_version deb deb-src clean tarball
