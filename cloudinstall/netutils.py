#
# netutils.py - Helper utilies for cloud installer
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

from ipaddress import IPv4Interface, ip_address
from netaddr import IPSet
import re
from subprocess import check_output


def _networkinfo(interface):
    """Given an interface name, returns dict containing network and
    broadcast address as IPv4Interface objects

    If an interface has no IP, returns None
    """
    ipcmds = "ip -o -4 address show dev {}".format(interface).split()
    out = check_output(ipcmds).decode('utf-8')
    nwmatch = re.search("inet (\d+\.\d+\.\d+\.\d+/\d+)", out)
    if nwmatch is None:
        return None
    nw = IPv4Interface(nwmatch.groups()[0])

    bcastaddrmatch = re.search("brd (\d+\.\d+\.\d+\.\d+)", out)
    if bcastaddrmatch is None:
        return None

    bcastaddr = IPv4Interface(bcastaddrmatch.groups()[0])
    return dict(network=nw, bcastaddr=bcastaddr)


def get_ip_addr(interface):
    info = _networkinfo(interface)
    if info is None:
        return None
    return str(info['network'].ip)


def get_bcast_addr(interface):
    info = _networkinfo(interface)
    if info is None:
        return None
    return str(info['bcastaddr'].ip)


def get_network(interface):
    info = _networkinfo(interface)
    if info is None:
        return None
    return str(info['network'])


def get_netmask(interface):
    info = _networkinfo(interface)
    if info is None:
        return None
    info = info['network'].with_netmask
    return info.split('/')[-1]


def get_ip_set(cidr):
    """ Returns a list of ip's in cidr for use in juju's no-proxy setting
    """
    ips = list(IPSet([cidr]))
    return ",".join(str(x) for x in ips)


def get_default_gateway():
    """ get first listed network gateway from 'route -n'.

    TODO: this does not handle the case where multiple gateways exist.
    just directly copied from original shell code.
    """

    out = check_output("route -n | awk 'index($4, \"G\") { print $2 }'",
                       shell=True)
    return out.decode('utf-8').splitlines()[0]


def get_network_interfaces():
    """ Get network interfaces

    :returns: available interfaces and their properties
    :rtype: list
    """
    out = check_output(['ifconfig', '-s']).decode()
    _ifconfig = out.split('\n')[1:-1]
    rd = {}
    for i in _ifconfig:
        name = i.split(' ')[0]
        if 'lo' in name:
            continue
        ip_addr = get_ip_addr(name)
        if ip_addr is None:
            continue
        rd[name] = dict(ipaddress=get_ip_addr(name),
                        broadcast=get_bcast_addr(name),
                        netmask=get_netmask(name))
    return rd


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
