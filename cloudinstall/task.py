# Copyright 2014, 2015 Canonical, Ltd.
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

import logging
import os
import time
import yaml

from cloudinstall import utils
from cloudinstall import async
from cloudinstall.alarms import AlarmMonitor
from cloudinstall.config import Config

log = logging.getLogger('cloudinstall.task')


class Tasker:

    """ Provides progress updates and task tracking.

    To use: register a list of task names using register_tasks:
    self.register_tasks(["A", "B", "C"])

    Then, in that same order, as tasks are started, call start_task:

    self.start_task("A")
    ... do A
    self.start_task("B")
    ... do B, wait for user input or do something that isn't C
    self.stop_current_task()
    self.start_task("C")
    ... do C

    """

    def __init__(self, display_controller, loop, config):
        self.config = config
        self.display_controller = display_controller
        self.loop = loop
        self.tasks = []  # (name, starttime, endtime=None)
        self.tasks_started_debug = []
        self.current_task_index = 0
        # stop_current_task can be called from any thread, and uses
        # stopped to tell update to not reschedule itself.
        self.stopped = False
        self.alarm = None
        self.task_info_func = None

    def register_tasks(self, tasks):
        self.tasks = [(n, None, None) for n in tasks]
        self.max_width = max([len(n) for n in tasks])

    def start_task(self, newtaskname, task_info_func=None):
        self.task_info_func = task_info_func
        self.tasks_started_debug.append(newtaskname)

        if len(self.tasks) <= self.current_task_index:
            log.error("ran off end of task list, "
                      "can't start {}".format(newtaskname))
            return

        (n, s, e) = self.tasks[self.current_task_index]
        if s is not None and e is None:
            self.stop_current_task()
            if len(self.tasks) <= self.current_task_index:
                log.error("ran off end of task list")
                return

        (expectedname, _, _) = self.tasks[self.current_task_index]
        if expectedname != newtaskname:
            log.warning("task name: expected {}, got {}".format(expectedname,
                                                                newtaskname))
            log.info("tasks        : {}\n"
                     "tasks_started: {}".format(self.tasks,
                                                self.tasks_started_debug))

        self.tasks[self.current_task_index] = (expectedname,
                                               time.time(), None)
        self.stopped = False
        if self.alarm is None:
            self.update_progress()
        self.write_timings()

    def write_timings(self):
        readable_tasks = []
        for n, s, e in self.tasks:
            if e is not None and s is not None:
                timing = e - s
            else:
                timing = None
            readable_tasks.append((n, s, e, timing))

        utils.spew(os.path.join(self.config.cfg_path, 'timings.yaml'),
                   yaml.dump(readable_tasks),
                   utils.install_user())

    def stop_current_task(self):
        if self.current_task_index >= len(self.tasks):
            log.error("stop_current_task called too many times, skipping.\n "
                      "self.tasks={}\nself.current_task_index={}\n"
                      "tasks_started: {}".format(self.tasks,
                                                 self.current_task_index,
                                                 self.tasks_started_debug))
            return
        n, s, _ = self.tasks[self.current_task_index]
        self.tasks[self.current_task_index] = (n, s, time.time())
        self.current_task_index += 1
        self.stopped = True
        self.write_timings()

    def update_progress(self, loop=None, userdata=None):
        self.alarm = None
        if self.stopped:
            # if stopped was set in a separate thread, return and
            # do not reschedule.
            return

        m = []
        for (n, s, e) in self.tasks:
            if s is None:
                m.append(('label', "{n:>{mw}}: "
                          "{ts:<22}\n".format(n=n, mw=self.max_width,
                                              ts='   -')))
            elif e is None:
                e = time.time()
                ts = "{:6d} sec(s) elapsed".format(int(e) - int(s))
                m.append("{n:>{mw}}: {ts:<22}"
                         "\n".format(n=n, mw=self.max_width, ts=ts))
                if self.task_info_func:
                    m.append(('label',
                              "\n{}\n\n".format(self.task_info_func())))
            else:
                ts = "{:6d} sec".format(int(e) - int(s))
                m.append(('label', "{n:>{mw}}: {ts:<22}"
                          "\n".format(n=n, mw=self.max_width,
                                      ts=ts)))

        if self.display_controller.node_install_wait_view is None:
            self.display_controller.render_node_install_wait(m)
        else:
            self.display_controller.node_install_wait_view.message.set_text(m)
            self.display_controller.node_install_wait_view.redraw_kitt()
        f = self.update_progress
        self.alarm = self.loop.set_alarm_in(0.3, f)
        AlarmMonitor.add_alarm(self.alarm, "tasker-update-progress")


class TaskerConsole:

    """ Console tasker """

    def __init__(self, display_controller, loop, config):
        self.loop = loop
        self.config = config
        self.display_controller = display_controller
        self.tasks = []

    def start_task(self, taskname, task_info_func=None):
        log.info(taskname)

    def stop_current_task(self):
        pass

    def register_tasks(self, tasks):
        self.tasks.extend(tasks)


class FakeInstall:

    """For testing only, use as a replacement for MultiInstall*"""

    def __init__(self, loop, display_controller):
        super().__init__(display_controller, loop)
        self.config = Config()
        self.tasker = Tasker(display_controller, loop)
        self.display_controller = display_controller

    def run(self):
        self.tl = ['a', 'b', 'c']
        self.tasker.register_tasks(self.tl)
        self.update_progress()
        async.submit(self.async_go,
                     self.display_controller.show_exception_message)

    def async_go(self):
        for t in self.tl:
            self.tasker.start_task(t)
            time.sleep(1.2)
        raise Exception("ERROR IN ASYNC GO")
        self.tasker.stop_current_task()
