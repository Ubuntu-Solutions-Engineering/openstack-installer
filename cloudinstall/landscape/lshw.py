#
# Copyright 2005-2012, 2014 Canonical, Ltd.
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

from lxml import etree


class LSHWParser(object):
    """Parser for the  XML output of the "lshw" command."""

    DISK_FIELDS = ("vendor", "product", "description", "logicalname", "size")

    def __init__(self, data):
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        self._doc = etree.XML(data, parser)

    def get_disks(self):
        """Return a list of dicts with info about disks."""
        nodes = []

        for node in self._get_nodes(_id="disk"):
            fields = self._get_fields(node, self.DISK_FIELDS)
            # In the lshw output reported by MaaS, the commisioning disk can be
            # included (lp:1318382), we skip it since it's not a real disk on
            # the computer.
            if fields["product"] == "VIRTUAL-DISK":
                continue

            nodes.append(fields)
        return nodes

    def _get_nodes(self, parent=None, tag="node", _id=None, _class=None):
        """
        Return nodes with the specified tag, possibly filtering by id or class
        attributes.

        @param parent: the node to search from, if C{None} the whole doc is
            searched.
        @param tag: the node tag to search for.
        @param _id: if specified, value of the id attribute to limit the
            search to.
        @param _class: if specified, value of the id attribute to limit the
            search to.
        @return a list of elements
        """
        if parent is None and self._doc is None:
            return []

        expr = "//" + tag if parent is None else tag
        if _id:
            # We use contains here because multiple disks under a common parent
            # will be reprented as disk:0 disk:1, yet a singleton is just disk
            expr += "[contains(@id, '%s')]" % _id
        if _class:
            expr += "[@class='%s']" % _class

        find = self._doc.xpath if parent is None else parent.xpath
        return find(expr)

    def _get_fields(self, node, fields):
        """
        Return a dict mapping tag names to text for children of the node with
        specified tags.
        """
        values = {}
        for field in fields:
            field_node = node.find(field)
            values[field] = self._get_text(field_node)
        return values

    def _get_text(self, node):
        if node is None:
            return None
        return node.text
