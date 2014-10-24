#
# Makefile for cloud-install
#
NAME        = openstack
TOPDIR      := $(shell basename `pwd`)
GIT_REV     := $(shell git log --oneline -n1| cut -d" " -f1)
VERSION     := $(shell ./tools/version)

$(NAME)_$(VERSION).orig.tar.gz: clean
	cd .. && tar czf $(NAME)_$(VERSION).orig.tar.gz $(TOPDIR) --exclude-vcs --exclude=debian

tarball: $(NAME)_$(VERSION).orig.tar.gz

.PHONY: install-dependencies
install-dependencies:
	sudo apt-get -yy install devscripts equivs
	sudo mk-build-deps -i -t "apt-get --no-install-recommends -y" debian/control

.PHONY: uninstall-dependencies
uninstall-dependencies:
	sudo apt-get remove openstack-build-deps

# sudo make uninstall type=single-system
# (or just sudo make uninstall)
.PHONY: uninstall
uninstall: uninstall-dependencies
	sudo tools/cloud-uninstall ${type}

clean:
	@debian/rules clean
	@rm -rf debian/cloud-install
	@rm -rf docs/_build/*
	@rm -rf ../openstack_*.deb ../cloud-*.deb ../openstack_*.tar.gz ../openstack_*.dsc ../openstack_*.changes \
		../openstack_*.build ../openstack-*.deb

deb-src: clean update_version tarball
	@debuild -S -us -uc

deb: clean update_version tarball
	@debuild -us -uc -i

# TODO: Disable for now, will be removed in a later release.
# sbuild: clean update_version tarball
#	@sbuild -d trusty-amd64 -j4

current_version:
	@echo $(VERSION)

git_rev:
	@echo $(GIT_REV)

update_version:
	wrap-and-sort
	@sed -i -r "s/(^__version__\s=\s)(.*)/\1\"$(VERSION)\"/" cloudinstall/__init__.py

.PHONY: ci-test pyflakes pep8 test travis-test
ci-test: pyflakes pep8 travis-test

pyflakes:
	python3 `which pyflakes` cloudinstall test

pep8:
	pep8 cloudinstall test

$(HOME)/.cloud-install:
	mkdir -p $(HOME)/.cloud-install

NOSE_ARGS = -v --with-cover --cover-package=cloudinstall --cover-html test --cover-inclusive cloudinstall
test: $(HOME)/.cloud-install
	nosetests3 $(NOSE_ARGS)

travis-test: $(HOME)/.cloud-install
	nosetests $(NOSE_ARGS)

gooview:
	PYTHONPATH=$(shell pwd):$(PYTHONPATH) tools/gooview.py

status:
	PYTHONPATH=$(shell pwd):$(PYTHONPATH) bin/cloud-status

# Indirection to allow 'make run' to build deb automatically, but
# 'make sbuild; make run' will not invoke 'deb'.
../openstack*.deb: deb
	echo "rule to make .deb automatically"

.PHONY: install
install: ../openstack*.deb
	-dpkg -i ../openstack*deb
	-dpkg -i ../openstack-${type}*deb
	apt-get -yy install -f


# sudo make run type=multi proxy=http://localhost:3128/
.PHONY: run
run: install
	MAAS_HTTP_PROXY=${proxy} openstack-install

# sudo make landscape
.PHONY: landscape
landscape: ../openstack*.deb
	-dpkg -i ../openstack*deb
	-dpkg -i ../openstack-multi*deb
	-dpkg -i ../openstack-landscape*deb
	apt-get -yy install -f
	@echo please follow the instructions in
	@echo "/usr/share/openstack/templates/landscape-deployments.yaml"
	@echo and then run `sudo cloud-install` as usual


all: deb
