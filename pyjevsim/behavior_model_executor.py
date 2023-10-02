"""
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""

from abc import abstractmethod

from .behavior_executor import BehaviorExecutor
from .behavior_model import BehaviorModel
from .definition import *


class BehaviorModelExecutor(BehaviorExecutor):
    def __init__(
        self, itime=Infinite, dtime=Infinite, ename="default", behavior_model=""
    ):
        super().__init__(itime, dtime, ename, behavior_model)


"""        
    def ext_trans(self, port, msg):
        super().ext_trans(port, msg)

    # Internal Transition
    def int_trans(self):
        super().int_trans()
        pass

    # Output Function
    def output(self):
        return super().output()

    # Time Advanced Function
    def time_advance(self):
        return super().time_advance()
"""
