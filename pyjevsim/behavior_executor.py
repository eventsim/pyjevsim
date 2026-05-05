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

        # Hot-path attribute snapshots. obj_id and destruct_t never change
        # over the executor's lifetime, so we read them once here instead
        # of dispatching through method chains every time the scheduler
        # needs an id.
        self._cached_destruct_time = self._destruct_t
        self._obj_id = behavior_model.get_obj_id()

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
        """Returns the destruction time (cached for performance)"""
        return self._cached_destruct_time

    def get_obj_id(self):
        """Returns the object ID. Snapshot of the model's id, taken at
        construction time to skip the `BehaviorModel` -> `SystemObject`
        method dispatch on the hot path."""
        return self._obj_id

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
        if self.behavior_model.get_cancel_flag():
            self._cancel_reschedule_f = True

        self.behavior_model.ext_trans(port, msg)

    # Internal Transition
    def int_trans(self):
        """Handles internal transition"""
        self.behavior_model.int_trans()

    # Confluent Transition
    def con_trans(self, port_msgs):
        """Handles confluent transition (model is both imminent and
        receiving external events at the same simulated instant).

        Args:
            port_msgs (Iterable[tuple[str, SysMessage]]): bag of messages
                with their input ports.
        """
        if self.behavior_model.get_cancel_flag():
            self._cancel_reschedule_f = True

        self.behavior_model.con_trans(port_msgs)

    # Output Function
    def output(self, msg_deliver):
        """Executes the output function of the behavior model"""
        return self.behavior_model.output(msg_deliver)

    # Time Advance Function
    def time_advance(self):
        """Returns the time advance value for the current state"""
        if self.behavior_model._cur_state in self.behavior_model._states:
            return self.behavior_model._states[self.behavior_model._cur_state]

        return -1

    def set_req_time(self, global_time):
        """Set the executor's next request time.

        This is the single hottest method on the simulator's inner loop —
        called once per affected model per tick. The body is inlined to
        avoid the `set_global_time` -> `time_advance` -> dict-lookup
        method-dispatch chain that the previous version went through.
        """
        bm = self.behavior_model
        self.global_time = global_time
        bm.global_time = global_time

        # Inlined `time_advance`: read state and look up its deadline.
        ta = bm._states.get(bm._cur_state, -1)

        if ta == Infinite:
            self._next_event_t = Infinite
            self.request_time = Infinite
        elif self._cancel_reschedule_f:
            self.request_time = min(self._next_event_t, global_time + ta)
        else:
            self.request_time = global_time + ta

    def get_req_time(self):
        """Returns the request time and resets the cancel flag if necessary"""
        if self._cancel_reschedule_f:
            self._cancel_reschedule_f = False
            self.behavior_model.reset_cancel_flag()
        self._next_event_t = self.request_time
        return self.request_time
    