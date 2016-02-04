#!/bin/bash -ex

OSI_TESTRUNNER_ID=battlemidgetjenkins sudo -E openstack-install -c \
                 $WORKSPACE/openstack-tests/profiles/lds.yaml \
                 --constraints "mem=16 tags=autopilot"

py.test-3 $WORKSPACE/integration/tests/test_autopilot.py
