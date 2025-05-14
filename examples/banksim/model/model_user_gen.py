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
from pyjevsim.system_executor import SysExecutor
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

    def __str__(self):
        """
        Returns a string representation of the BankUser.

        Returns:
            str: String representation
        """
        return f"{self.get_id()}, {self.service_t}, {self.arrival_t}, {self.done_t}, {self.wait_t}"


class BankUserGenerator(BehaviorModel):
    """A Model representing a bank user generator."""

    def __init__(self, name):
        """
        Args:
            name (str): Name of Model
            cycle (float): Generation cycle time
            max_user (int): Maximum number of users to generate
            proc_time (float): Processing time for each user
        """
        BehaviorModel.__init__(self, name)
        self.init_state("WAIT")  # Initialize initial state
        self.insert_state("WAIT", Infinite)  # Add "WAIT" state
        self.insert_state("GEN", random.randint(1,10))  # Add "GEN" state with cycle time

        self.insert_input_port("start")  # Add input port "start"
        self.insert_output_port("user_out")  # Add output port "user_out"

        #self.cycle = cycle  # Generation cycle time
        self.generated_user = 0  # Counter for generated users
        #self.max_user = max_user  # Maximum number of users to generate
        #self.proc_time = proc_time  # Processing time for each user
        
    def ext_trans(self, port, msg):
        """
        Handles external transitions based on the input port.

        Args:
            port (str): The port that received the message
            msg (SysMessage): The received message
        """
        if port == "start":
            #print(f"[Gen][IN]: started")
            self._cur_state = "GEN"  # Transition state to "GEN"        
            self.update_state("GEN", random.randint(1,10))
        if port == "stop" :
            self._cur_satate = "WAIT"

    def output(self, msg_deliver):
        """
        Generates the output message when in the "GEN" state.

        Returns:
            SysMessage: The output message
        """
        _time = self.global_time
        #print(f"[G] ID:{self.get_name()}-{self.generated_user} Time:{_time}")

        msg = SysMessage(self.get_name(), "user_out")

        bu = BankUser(f"{self.get_name()}-{self.generated_user}", random.randint(1, 10))
        bu.set_arrival_time(_time)
        msg.insert(bu)  # Insert BankUser into message

        self.generated_user += 1  # Increment generated user count
        msg_deliver.insert_message(msg)
        
        return msg_deliver

    def int_trans(self):
        """Handles internal transitions based on the current state."""
        self.update_state("GEN", random.randint(1,10))  # Update "GEN" state with cycle time
        
        #xprint("state update : ", self._states["GEN"])
        
    def get_user(self) : 
        return self.generated_user
    
    def set_state_idle(self) :
        self._cur_state = "WAIT"