#
# Makefile for cloud-install
#
NAME        = cloud-installer
TOPDIR      := $(shell basename `pwd`)
GIT_REV     := $(shell git log --oneline -n1| cut -d" " -f1)
VERSION     := $(shell ./tools/version)

$(NAME)_$(VERSION).orig.tar.gz: clean
	cd .. && tar czf $(NAME)_$(VERSION).orig.tar.gz $(TOPDIR) --exclude-vcs --exclude=debian

tarball: $(NAME)_$(VERSION).orig.tar.gz

.PHONY: install-dependencies
install-dependencies:
	sudo apt-get install debhelper python3-setuptools python3-requests \
		python3-requests-oauthlib python3-urwid python3-yaml python3-ws4py \
		python3-mock python3-nose devscripts python3-all python3-passlib

clean:
	@debian/rules clean
	@rm -rf debian/cloud-install

deb-src: clean update_version tarball
	@debuild -S -us -uc

deb: clean update_version tarball
	@debuild -us -uc -i

sbuild: clean update_version tarball
	@sbuild -d trusty-amd64 -j4

current_version:
	@echo $(VERSION)

git_rev:
	@echo $(GIT_REV)

update_version:
	wrap-and-sort
	@sed -i -r "s/(^__version__\s=\s)(.*)/\1\"$(VERSION)\"/" cloudinstall/__init__.py

status:
	PYTHONPATH=$(shell pwd):$(PYTHONPATH) bin/cloud-status

all: deb
