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

""" Async Handler
Provides async operations for various api calls and other non-blocking
work.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
log = logging.getLogger("cloudinstall.async")


AsyncPool = ThreadPoolExecutor(1)
log.debug('AsyncPool={}'.format(AsyncPool))


def submit(func, exc_callback):
    def cb(cb_f):
        e = cb_f.exception()
        if e:
            exc_callback(e)
    f = AsyncPool.submit(func)
    f.add_done_callback(cb)
