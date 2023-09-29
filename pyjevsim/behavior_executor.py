from abc import abstractmethod
#from core_model import CoreModel
#from behavior_model import BehaviorModel
from definition import *

class BehaviorExecutor:
    def __init__(self, itime=Infinite, dtime=Infinite, ename="default", behavior_model = None):
        self.engine_name = ename
        self._instance_t = itime
        self._destruct_t = dtime
            
        self._next_event_t = 0
        self._cur_state = ""
        self.RequestedTime = float("inf")
        self._not_available = None

        # 2023.09.26 jylee
        self.bm = behavior_model
        
        # 2021.10.16 cbchoi
        self._cancel_reschedule_f = False

    def __str__(self):
        return "[N]:{0}, [S]:{1}".format(self.get_name(), self._cur_state)

# removed by jylee 2023.09.26
#    def cancel_rescheduling(self):
#       self._cancel_reschedule_f = True

    def get_name(self) : 
        return self.bm.get_name()

    def get_engine_name(self):
        return self.engine_name

    def set_engine_name(self, engine_name):
        self.engine_name = engine_name

    def get_create_time(self):
        return self._instance_t

    def get_destruct_time(self):
        return self._destruct_t

    def get_obj_id(self):
        return self.bm.get_obj_id()

    # state management
    def get_cur_state(self):
        return self._cur_state

    def init_state(self, state):
        self._cur_state = state

    # External Transition
    def ext_trans(self, port, msg):
        if self.bm.get_cancel_flag() :
            self._cancel_reschedule_f = True
        
        self.bm.ext_trans(port, msg)
        pass

    # Internal Transition
    def int_trans(self):
        self.bm.int_trans()
        pass

    # Output Function
    def output(self):
        return self.bm.output()

    # Time Advanced Function
    def time_advance(self):   
        if self.bm._cur_state in self.bm._states:    
            return self.bm._states[self.bm._cur_state]
        else:
            return -1

    def set_req_time(self, global_time, elapsed_time=0):
        if self.time_advance() == Infinite:
            self._next_event_t = Infinite
            self.RequestedTime = Infinite
        else:
            if self._cancel_reschedule_f:
                self.RequestedTime = min(self._next_event_t, global_time + self.time_advance())
            else:
                self.RequestedTime = global_time + self.time_advance()

    def get_req_time(self):    
        if self._cancel_reschedule_f:
            self._cancel_reschedule_f = False
            self.bm.reset_cancel_flag()
        self._next_event_t = self.RequestedTime
        return self.RequestedTime
