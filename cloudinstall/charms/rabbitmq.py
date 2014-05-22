#
# rabbitmq.py - RabbitMQ Charm instructions
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

from cloudinstall.charms import CharmBase


class CharmRabbitMQ(CharmBase):
    """ RabbitMQ directives """

    charm_name = 'rabbitmq-server'
    display_name = 'RabbitMQ Server'

__charm_class__ = CharmRabbitMQ
