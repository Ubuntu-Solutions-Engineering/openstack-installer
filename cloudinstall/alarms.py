# Copyright 2015 Canonical, Ltd.
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

""" Alarm monitor
"""


class AlarmMonitor:
    alarms = {}
    loop = None

    @classmethod
    def add_alarm(cls, handle, name):
        if name in cls.alarms:
            cls.loop.remove_alarm(cls.alarms[name])
        cls.alarms[name] = handle

    @classmethod
    def remove_all(cls):
        for alarm in cls.alarms.values():
            cls.loop.remove_alarm(alarm)
        cls.alarms = {}
