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
import re
from subprocess import check_output


def _networkinfo(interface):
    ipcmds = "ip -o -4 address show dev {}".format(interface).split()
    out = check_output(ipcmds).decode('utf-8')
    nw = re.search("inet (\d+\.\d+\.\d+\.\d+/\d+)", out).groups()[0]
    nw = IPv4Interface(nw)
    bcastaddr = re.search("brd (\d+\.\d+\.\d+\.\d+)", out).groups()[0]
    bcastaddr = IPv4Interface(bcastaddr)
    return dict(network=nw, bcastaddr=bcastaddr)


def get_ip_addr(interface):
    return str(_networkinfo(interface)['network'].ip)


def get_bcast_addr(interface):
    return str(_networkinfo(interface)['bcastaddr'].ip)


def get_network(interface):
    return str(_networkinfo(interface)['network'])


def get_netmask(interface):
    info = _networkinfo(interface)['network'].with_netmask
    return info.split('/')[-1]


def get_default_gateway():
    """ get first listed network gateway from 'route -n'.

    TODO: this does not handle the case where multiple gateways exist.
    just directly copied from original shell code.
    """

    out = check_output("route -n | awk 'index($4, \"G\") { print $2 }'",
                       shell=True)
    return out.decode('utf-8').splitlines()[0]


def get_network_interface(iface):

    """ Get network interface properties

    :param iface: Interface to query (ex. eth0)
    :type iface: str
    :return: interface properties or empty if none
    :rtype: dict

    .. code::

        # Get address, broadcast, and netmask of eth0
        iface = utils.get_network_interface('eth0')
    """
    out = check_output(['ifconfig', iface]).decode()
    line = out.split('\n')[1:2][0].lstrip()
    regex = re.compile('^inet addr:([0-9]+(?:\.[0-9]+){3})\s+'
                       'Bcast:([0-9]+(?:\.[0-9]+){3})\s+'
                       'Mask:([0-9]+(?:\.[0-9]+){3})')
    match = re.match(regex, line)
    if match:
        return {'address': match.group(1),
                'broadcast': match.group(2),
                'netmask': match.group(3)}
    return {}


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
        if 'lo' not in name:
            rd[name] = get_network_interface(name)
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
