"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains a BehaviorExecutor, an object for executing a BehaviorModel.
"""

from .definition import Infinite
from .executor import Executor

class BehaviorExecutor(Executor):
    """
    A decorated form of the BehaviorModel, ready to be executed by the SysExecutor.
    Manages the simulation time of the BehaviorModel and the information in the SysExecutor.

    Args:
        itime (int or Infinite): Time of instance creation
        dtime (int or Infinite): Time of instance destruction
        ename (str): SysExecutor name
        behavior_model (ModelType.BEHAVIORAL): Behavior Model
    """
    def __init__(self, itime=Infinite, dtime=Infinite, ename="default", behavior_model=None, parent=None):
        super().__init__(itime, dtime, ename, behavior_model, parent)

        self._next_event_t = 0  # Next event time
        self._cur_state = ""  # Current state of the behavior executor
        self.request_time = float("inf")  # Request time initialized to infinity

        self.behavior_model = behavior_model #Behavior Model
        self._cancel_reschedule_f = False #cancel reschedule flag

    def set_global_time(self, gtime):
        """Sets the global time for the executor and behavior model"""
        self.global_time = gtime
        self.behavior_model.set_global_time(gtime)
        
    def get_core_model(self):
        """Returns the core behavior model"""
        return self.behavior_model

    def __str__(self):
        """Returns a string representation of the executor"""
        return f"[N]:{self.get_name()}, [S]:{self._cur_state}"

    def get_name(self):
        """Returns the name of the behavior model"""
        return self.behavior_model.get_name()

    def get_engine_name(self):
        """Returns the name of the engine"""
        return self.engine_name

    def set_engine_name(self, engine_name):
        """Sets the name of the engine"""
        self.engine_name = engine_name

    def get_create_time(self):
        """Returns the instance creation time"""
        return self._instance_t

    def get_destruct_time(self):
        """Returns the destruction time"""
        return self._destruct_t

    def get_obj_id(self):
        """Returns the object ID of the behavior model"""
        return self.behavior_model.get_obj_id()

    # State management
    def get_cur_state(self):
        """Returns the current state of the executor"""
        return self._cur_state

    def init_state(self, state):
        """Initializes the state of the executor"""
        self._cur_state = state

    # External Transition
    def ext_trans(self, port, msg):
        """Handles external transition based on port and message"""
        print("test")
        if self.behavior_model.get_cancel_flag():
            self._cancel_reschedule_f = True

        self.behavior_model.ext_trans(port, msg)

    # Internal Transition
    def int_trans(self):
        """Handles internal transition"""
        self.behavior_model.int_trans()

    # Output Function
    def output(self):
        """Executes the output function of the behavior model"""
        return self.behavior_model.output()

    # Time Advance Function
    def time_advance(self):
        """Returns the time advance value for the current state"""
        if self.behavior_model._cur_state in self.behavior_model._states:
            return self.behavior_model._states[self.behavior_model._cur_state]

        return -1

    def set_req_time(self, global_time):
        """Sets the request time based on the global time and time advance"""
        self.set_global_time(global_time)
        if self.time_advance() == Infinite:
            self._next_event_t = Infinite
            self.request_time = Infinite
        else:
            if self._cancel_reschedule_f:
                self.request_time = min(self._next_event_t, global_time + self.time_advance())
            else:
                self.request_time = global_time + self.time_advance()

    def get_req_time(self):
        """Returns the request time and resets the cancel flag if necessary"""
        if self._cancel_reschedule_f:
            self._cancel_reschedule_f = False
            self.behavior_model.reset_cancel_flag()
        self._next_event_t = self.request_time
        return self.request_time
    