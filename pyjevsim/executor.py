"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Executor, the parent class of all Executor Types. 
"""

class Executor:
    """Base class for executors."""
    def __init__(self, itime, dtime, ename):
        """
        Args:
            itime (float): Instance creation time
            dtime (float): Destruction time
            ename (str): Engine name
        """
        self.engine_name = ename 
        self._instance_t = itime 
        self._destruct_t = dtime
