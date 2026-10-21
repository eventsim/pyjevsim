"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Executor, the parent class of all Executor Types. 
"""

class Executor:
    """Base state shared by model executors.

    Scheduling order is managed by ``ScheduleQueue`` rather than comparison
    methods on executor instances.
    """

    def __init__(self, itime, dtime, ename, model, parent):
        """
        Args:
            itime (float): Instance creation time
            dtime (float): Destruction time
            ename (str): Engine name
        """
        self.engine_name = ename
        self._instance_t = itime
        self._destruct_t = dtime
        self.model = model
        self.parent = parent

    def _reschedule(self, global_time):
        """Set the request time for ``global_time`` and return it.

        ``ScheduleQueue.reschedule_all`` calls this once per affected
        executor in place of ``set_req_time`` followed by ``get_req_time``.
        """
        self.set_req_time(global_time)
        return self.get_req_time()
