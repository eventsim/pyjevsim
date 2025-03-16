"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Banksim Accountant Model 
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage

class BankAccountant(BehaviorModel):
    """A Model representing a bank accountant processing bank users."""

    def __init__(self, name, proc_num):
        """Initializes the BankAccountant with states and ports.

        Args:
            name (str): Name of the accountant
            proc_num (int): Processor number for identification
        """
        BehaviorModel.__init__(self, name)

        self.init_state("WAIT")  # Initialize initial state
        self.insert_state("WAIT", Infinite)  # Add "WAIT" state
        self.insert_state("PROC", 1)  # Add "PROC" state with duration 1

        self.insert_input_port("in")  # Add input port "in"
        self.insert_output_port("next")  # Add output port "next"

        self.proc_num = f"proc{proc_num}"  # Processor number
        self.user = None  # Current user being processed
        self.proc_user = []  # List of processed users
        
    def ext_trans(self, port, msg):
        """
        Handles external transitions based on the input port.

        Args:
            port (str): The port that received the message
            msg (SysMessage): The received message
        """
        _time = self.global_time
        if port == "in":
            self.user = msg.retrieve()[0]
            self._cur_state = "PROC"  # Transition state to "PROC"
            self.update_state("PROC", self.user.get_service_time())  # Update "PROC" state duration
            print(f"[A][arrive] ID:{self.user.get_id()} Time:{_time}")

    def output(self):
        """
        Generates the output message when in the "PROC" state.

        Returns:
            SysMessage: The output message
        """
        _time = self.global_time
        msg = None
        if self._cur_state == "PROC":
            cur_time = self.global_time
            self.user.calc_wait_time(cur_time)  # Calculate wait time
            self.proc_user.append(self.user)  # Add user to processed list
            print(f"[A][processed] ID:{self.user.get_id()} Time:{_time}")

            msg = SysMessage(self.get_name(), "next")
            msg.insert(self.proc_num)  # Insert processor number

        return msg

    def int_trans(self):
        """Handles internal transitions based on the current state."""
        if self._cur_state == "PROC":
            self._cur_state = "WAIT"  # Transition state to "WAIT"

    def __del__(self):
        """Destructor to print the log of processed users."""
        print(f"[{self.get_name()}-{self.proc_num} log]")
        print("user-name, process_time, arrival_time, done_time, wait_time")
        for user in self.proc_user:
            print(user)

    def __str__(self):
        """
        Returns a string representation of the BankAccountant.

        Returns:
            str: String representation
        """
        return f">> {self.get_name()}, State:{self._cur_state}, {self.user}"