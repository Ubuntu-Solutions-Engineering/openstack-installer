#!/bin/bash -ex

OSI_TESTRUNNER_ID=battlemidgetjenkins sudo -E openstack-install -c \
                 $OPENSTACK_CONFIG \
                 --constraints "mem=16 tags=autopilot"

py.test-3 $WORKSPACE/integration/tests/test_autopilot.py
