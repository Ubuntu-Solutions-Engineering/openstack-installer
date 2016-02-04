# openstack-tests
> Installer tests

# USAGE

On the system where the installer is run do the following:

```
$ sudo apt-get install python3-pytest
```

## Single Installer

```
py.test-3 tests/test_single.py
```

## Autopilot Installer

```
py.test-3 tests/test_autopilot.py
```

## Multi Installer

```
py.test-3 tests/test_multi.py
```
