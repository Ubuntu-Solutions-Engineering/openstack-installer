#!/usr/bin/env python3
#
# ip_range.py - Cloud install ip range utility
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from ipaddress import ip_address, ip_network
import sys
from sys import argv


def ip_range(network):
    """Return tuple of low, high IP address for given network"""
    num_addresses = network.num_addresses
    if num_addresses == 1:
        host = network[0]
        return host, host
    elif num_addresses == 2:
        return network[0], network[-1]
    else:
        return network[1], network[-2]


def ip_range_max(network, exclude):
    """Return tuple of low, high IP address for largest IP address range within
    the given network.

    Accepts a list of IP addresses to exclude.
    """
    if (network.num_addresses <= 2) or (len(exclude) == 0):
        return ip_range(network)

    current = range(0, 0)
    remaining = range(int(network[1]), int(network[-1]))
    excluded = sorted(set(exclude))
    for ex in excluded:
        e = int(ex)
        if e in remaining:
            index = remaining.index(e)
            if index != 0:
                r = remaining[:index]
                if len(r) > len(current):
                    current = r
            index += 1
            if index < len(remaining):
                remaining = remaining[index:]
            else:
                remaining = range(0, 0)
                break

    length = len(current)
    if length < len(remaining):
        current = remaining
    elif length == 0:
        return ip_range(network)

    return ip_address(current[0]), ip_address(current[-1])

if __name__ == "__main__":
    args = len(argv)
    if args == 1:
        sys.stderr.write("Missing arguments")
        sys.exit(1)

    network = ip_network(argv[1], strict=False)
    ip_low, ip_high = ip_range_max(
        network, [ip_address(arg) for arg in argv[2:]]) \
        if args >= 3 else ip_range(network)
    print(str(ip_low) + "-" + str(ip_high))
