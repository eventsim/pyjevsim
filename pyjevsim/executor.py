"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Executor, the parent class of all Executor Types. 
"""

class Executor:
    """Base class for executors.

    Note: ``__lt__`` is no longer defined. Ordering used to be settled
    by ``(request_time, obj_id)`` on the executor object itself, which
    forced two ``get_obj_id()`` method dispatches per heap comparison.
    All priority-queue ordering now lives in ``ScheduleQueue``, which
    stores ``(req_time, obj_id, entry_id, executor)`` tuples — Python
    settles the order on the first three immutable fields without ever
    comparing executor objects directly.
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
