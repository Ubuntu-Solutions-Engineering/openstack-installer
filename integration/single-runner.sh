#!/bin/bash -ex

OSI_TESTRUNNER_ID=battlemidgetjenkins sudo -E openstack-install -c $OPENSTACK_CONFIG

py.test-3 $WORKSPACE/integration/tests/test_single.py
