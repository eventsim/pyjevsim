from abc import abstractmethod
from behavior_model import BehaviorModel
from behavior_executor import BehaviorExecutor
from definition import *

class BehaviorModelExecutor(BehaviorExecutor):
    def __init__(self, itime=Infinite, dtime=Infinite, ename="default", behavior_model = ""):
        super().__init__(itime, dtime, ename, behavior_model)
        
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