"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains a BehaviorExecutor, an object for executing a BehaviorModel.
"""

from .behavior_model import BehaviorModel
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
        self.request_time = Infinite  # Request time initialized to infinity

        self.behavior_model = behavior_model #Behavior Model
        self._cancel_reschedule_f = False #cancel reschedule flag

        # Object identity and destruction time do not change after creation.
        self._cached_destruct_time = dtime
        self._obj_id = behavior_model.get_obj_id()

        # SysExecutor._run_instant calls the model directly (one Python frame
        # less per output/transition) when this executor's wrappers are the
        # plain forwarding ones defined below. The model's methods are still
        # looked up at call time, so patching the model class keeps working.
        # A subclass that overrides any wrapper (HLAExecutor.output, for
        # example) keeps ``_model_fast = None`` and is called as before.
        # The check runs once, here: replacing BehaviorExecutor.output/
        # int_trans/ext_trans/con_trans on the class (monkeypatching,
        # ``mock.patch.object``) or on an instance after this executor is
        # built is not seen by _run_instant. Subclass instead, or set
        # ``_model_fast = None`` on the executor to force the wrappers.
        # The direct path reads the model's cancel flag attribute instead of
        # calling get_cancel_flag(), so a model class that overrides
        # get_cancel_flag keeps the wrappers, which call it. getattr keeps a
        # duck-typed model without the method constructible.
        cls = type(self)
        if (cls.output is BehaviorExecutor.output
                and cls.int_trans is BehaviorExecutor.int_trans
                and cls.ext_trans is BehaviorExecutor.ext_trans
                and cls.con_trans is BehaviorExecutor.con_trans
                and getattr(type(behavior_model), "get_cancel_flag", None)
                    is BehaviorModel.get_cancel_flag):
            self._model_fast = behavior_model

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # The fused _reschedule below would bypass an overridden
        # set_req_time or get_req_time, so such subclasses call both. Compare
        # the resolved attributes so an override inherited from a mixin
        # (class X(Mixin, BehaviorExecutor)) is detected too.
        if "_reschedule" not in cls.__dict__ and (
                cls.set_req_time is not BehaviorExecutor.set_req_time
                or cls.get_req_time is not BehaviorExecutor.get_req_time):
            cls._reschedule = Executor._reschedule

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
        """Return the object ID captured when the executor was created."""
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
        """Handles external transition based on port and message.

        Read the cancellation flag after the model transition because
        ``cancel_rescheduling`` may set it during this call.
        """
        bm = self.behavior_model
        bm.ext_trans(port, msg)

        if bm.get_cancel_flag():
            self._cancel_reschedule_f = True

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
        bm = self.behavior_model
        bm.con_trans(port_msgs)

        if bm.get_cancel_flag():
            self._cancel_reschedule_f = True

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

        State lookup is kept inline because this method runs for each affected
        model after a transition.
        """
        bm = self.behavior_model
        self.global_time = global_time
        bm.global_time = global_time

        # Read the current state's time advance directly.
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

    def _reschedule(self, global_time):
        """``set_req_time(global_time)`` then ``get_req_time()`` in one call.

        Keep this in step with the two methods above. Subclasses that
        override either method (directly or through a mixin) fall back to
        ``Executor._reschedule``, which calls both. Replacing
        ``BehaviorExecutor.set_req_time``/``get_req_time`` on the class after
        import (monkeypatching, ``mock.patch.object``) is not seen by this
        fused path; patch ``_reschedule`` as well, or subclass instead.
        """
        bm = self.behavior_model
        self.global_time = global_time
        bm.global_time = global_time

        ta = bm._states.get(bm._cur_state, -1)

        if self._cancel_reschedule_f:
            if ta == Infinite:
                req_t = Infinite
            else:
                req_t = min(self._next_event_t, global_time + ta)
            self._cancel_reschedule_f = False
            bm.reset_cancel_flag()
        elif ta == Infinite:
            req_t = Infinite
        else:
            req_t = global_time + ta
        self.request_time = req_t
        self._next_event_t = req_t
        return req_t
