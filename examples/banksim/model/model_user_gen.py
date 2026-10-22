"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Banksim User Generator Model 
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage
import random

class BankUser:  
    def __init__(self, _id: int, s_t: float):
        """
        Args:
            _id (int): User ID
            s_t (float): Service time
        """
        self.user_id = _id      # User ID
        self.wait_t = 0.0       # Wait time
        self.done_t = 0.0       # Done time
        self.arrival_t = 0.0    # Arrival time
        self.service_t = s_t    # Service time
        self.drop_t = 0

    def get_id(self) -> int:
        """        
        Returns:
            int: User ID
        """
        return self.user_id

    def get_wait_time(self) -> float:
        """
        Returns:
            float: Wait time
        """
        return self.wait_t

    def get_arrival_time(self) -> float:
        """
        Returns:
            float: Arrival time
        """
        return self.arrival_t

    def get_service_time(self) -> float:
        """
        Returns:
            float: Service time
        """
        return self.service_t

    def set_arrival_time(self, a_t: float) -> None:
        """
        Args:
            a_t (float): Arrival time
        """
        self.arrival_t = a_t

    def calc_wait_time(self, w_t: float) -> None:
        """
        Calculates the wait time.

        Args:
            w_t (float): Done time
        """
        self.done_t = w_t
        self.wait_t = w_t - self.arrival_t
        
    def set_drop_time(self, d_t: float) -> None:
        """
        Args:
            a_t (float): Arrival time
        """
        self.drop_t = d_t

    def __str__(self):
        """
        Returns a string representation of the BankUser.

        Returns:
            str: String representation
        """
        return f"{self.get_id()}, {self.service_t}, {self.arrival_t}, {self.done_t}, {self.wait_t}"


class BankUserGenerator(BehaviorModel):
    """A Model representing a bank user generator.

    Input ports: ``start`` starts (or restarts) generation, ``stop`` stops it
    (the generator passivates until the next ``start``).  Output port:
    ``user_out``, one :class:`BankUser` per generation cycle.
    """

    # Random stream of an instance built without ``rng``: ``None`` means the
    # module-level ``random`` functions, looked up at every draw, exactly as
    # before the ``rng`` parameter existed.  It is a class attribute so that
    # such an instance has no extra instance attribute (its state, pickles and
    # snapshots are unchanged).
    _rng = None

    def __init__(self, name, rng=None):
        """
        Args:
            name (str): Name of Model
            rng (random.Random, optional): Random stream for the cycle and
                service times of this generator.  ``None`` (the default)
                draws from the module-level ``random``, i.e. the global
                stream shared by every unseeded generator.  Pass a
                dedicated ``random.Random`` (for example from
                ``examples.banksim.seeding.model_rng``) for a run that is
                reproducible and independent of the order in which
                same-time generators are processed.
        """
        BehaviorModel.__init__(self, name)
        if rng is not None:
            self._rng = rng
        self.init_state("WAIT")  # Initialize initial state
        self.insert_state("WAIT", Infinite)  # Add "WAIT" state
        self.insert_state("GEN", self._randint(1,10))  # Add "GEN" state with cycle time

        self.insert_input_port("start")  # Add input port "start"
        self.insert_input_port("stop")  # Add input port "stop"
        self.insert_output_port("user_out")  # Add output port "user_out"

        self.generated_user = 0  # Counter for generated users

    def _randint(self, a, b):
        """``randint(a, b)`` from this generator's stream (see ``_rng``)."""
        rng = self._rng
        if rng is None:
            return random.randint(a, b)
        return rng.randint(a, b)

    def ext_trans(self, port, msg):
        """
        Handles external transitions based on the input port.

        Args:
            port (str): The port that received the message
            msg (SysMessage): The received message
        """
        if port == "start":
            self._cur_state = "GEN"  # Transition state to "GEN"        
            self.update_state("GEN", self._randint(1,10))
        if port == "stop" :
            self._cur_state = "WAIT"

    def output(self, msg_deliver):
        """
        Generates the output message when in the "GEN" state.

        Returns:
            SysMessage: The output message
        """
        _time = self.global_time

        msg = SysMessage(self.get_name(), "user_out")

        bu = BankUser(f"{self.get_name()}-{self.generated_user}", self._randint(1, 10))
        bu.set_arrival_time(_time)
        msg.insert(bu)  # Insert BankUser into message

        self.generated_user += 1  # Increment generated user count
        msg_deliver.insert_message(msg)
        
        return msg_deliver

    def int_trans(self):
        """Handles internal transitions based on the current state."""
        self.update_state("GEN", self._randint(1,10))  # Update "GEN" state with cycle time
        
        
    def get_user(self) : 
        return self.generated_user
    
    def set_state_idle(self) :
        """Set the state to WAIT from outside a transition.

        The engine is not told: the generator still emits the user it has
        scheduled and passivates after that internal transition.  Send an
        event to the ``stop`` port to stop it at the current instant.
        """
        self._cur_state = "WAIT"
