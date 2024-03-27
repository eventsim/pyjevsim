"""
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""

from .definition import Infinite
from .executor import Executor


class BehaviorExecutor(Executor):
    def __init__(
        self, itime=Infinite, dtime=Infinite, ename="default", behavior_model=None
    ):
        super().__init__(itime, dtime, ename)

        self._next_event_t = 0
        self._cur_state = ""
        self.request_time = float("inf")

        # 2023.09.26 jylee
        self.behavior_model = behavior_model
        # 2021.10.16 cbchoi
        self._cancel_reschedule_f = False

    def set_global_time(self, gtime) : 
        self.global_time = gtime
        self.behavior_model.set_global_time(gtime)
        
    def get_core_model(self):
        return self.behavior_model

    def __str__(self):
        return f"[N]:{self.get_name()}, [S]:{self._cur_state}"

    # removed by jylee 2023.09.26
    #    def cancel_rescheduling(self):
    #       self._cancel_reschedule_f = True

    def get_name(self):
        return self.behavior_model.get_name()

    def get_engine_name(self):
        return self.engine_name

    def set_engine_name(self, engine_name):
        self.engine_name = engine_name

    def get_create_time(self):
        return self._instance_t

    def get_destruct_time(self):
        return self._destruct_t

    def get_obj_id(self):
        return self.behavior_model.get_obj_id()

    # state management
    def get_cur_state(self):
        return self._cur_state

    def init_state(self, state):
        self._cur_state = state

    # External Transition
    def ext_trans(self, port, msg):
        if self.behavior_model.get_cancel_flag():
            self._cancel_reschedule_f = True

        self.behavior_model.ext_trans(port, msg)

    # Internal Transition
    def int_trans(self):
        self.behavior_model.int_trans()

    # Output Function
    def output(self):
        return self.behavior_model.output()

    # Time Advanced Function
    def time_advance(self):
        if self.behavior_model._cur_state in self.behavior_model._states:
            return self.behavior_model._states[self.behavior_model._cur_state]

        return -1

    def set_req_time(self, global_time):
        self.set_global_time(global_time)
        if self.time_advance() == Infinite:
            self._next_event_t = Infinite
            self.request_time = Infinite
        else:
            if self._cancel_reschedule_f:
                self.request_time = min(
                    self._next_event_t, global_time + self.time_advance()
                )
            else:
                self.request_time = global_time + self.time_advance()

    def get_req_time(self):
        if self._cancel_reschedule_f:
            self._cancel_reschedule_f = False
            self.behavior_model.reset_cancel_flag()
        self._next_event_t = self.request_time
        return self.request_time
