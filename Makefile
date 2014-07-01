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
	sudo apt-get install devscripts equivs
	sudo mk-build-deps -i debian/control

.PHONY: uninstall-dependencies
uninstall-dependencies:
	sudo apt-get remove cloud-installer-build-deps

# sudo make uninstall type=single-system
# (or just sudo make uninstall)
.PHONY: uninstall
uninstall: uninstall-dependencies
	sudo tools/cloud-uninstall ${type}

clean:
	@debian/rules clean
	@rm -rf debian/cloud-install
	@rm -rf docs/_build/*
	@rm -rf ../cloud-*.deb ../cloud-*.tar.gz ../cloud-*.dsc ../cloud-*.changes \
		../cloud-*.build

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


.PHONY: ci-test pyflakes pep8 test
ci-test: pyflakes pep8 test

pyflakes:
	python3 `which pyflakes` cloudinstall

pep8:
	pep8 cloudinstall

test:
	mkdir -p $(HOME)/.cloud-install
	nosetests -v --with-cover --cover-package=cloudinstall --cover-html test

status:
	PYTHONPATH=$(shell pwd):$(PYTHONPATH) bin/cloud-status

# Indirection to allow 'make run' to build deb automatically, but
# 'make sbuild; make run' will not invoke 'deb'.
../cloud-installer*.deb: deb
	echo "rule to make .deb automatically"

# sudo make run type=multi proxy=http://localhost:3128/
.PHONY: run
run: ../cloud-installer*.deb
	-dpkg -i ../cloud-installer*deb
	-dpkg -i ../cloud-install-${type}*deb
	apt-get -yy install -f
	MAAS_HTTP_PROXY=${proxy} cloud-install

# sudo make landscape
.PHONY: landscape
landscape: ../cloud-installer*.deb
	-dpkg -i ../cloud-installer*deb
	-dpkg -i ../cloud-install-multi*deb
	-dpkg -i ../cloud-install-landscape*deb
	apt-get -yy install -f
	@echo please follow the instructions in
	@echo "/usr/share/cloud-installer/templates/landscape-deployments.yaml"
	@echo and then run `sudo cloud-install` as usual


all: deb
