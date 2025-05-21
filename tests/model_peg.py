"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Process Event Generator Model 
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage

class PEG(BehaviorModel):
    """Process Event Generator (PEG) class for generating events in a simulation."""

    def __init__(self, name):
        """
        Args:
            name (str): The name of Model
        """
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")                 # Initialize initial state
        self.insert_state("Wait", Infinite)     # Add "Wait" state
        self.insert_state("Generate", 1)        # Add "Generate" state

        self.insert_input_port("start")         # Add input port "start"
        self.insert_output_port("process")      # Add output port "process"

        self.msg_no = 0                         # Initialize message number

    def ext_trans(self, port, msg):
        """
        Handles external transitions based on the input port.
        
        Args:
            port (str): The port that received the message
            msg (SysMessage): The received message
        """
        #print("input start")
        if port == "start":
            print(f"[Gen][IN]: started")
            self._cur_state = "Generate"  # Transition state to "Generate"

    def output(self, msg_deliver):
        """
        Generates the output message when in the "Generate" state.
        
        Returns:
            MessageDeliverer: The output message
        """
        msg = SysMessage(self.get_name(), "process")
        msg.insert(f"{self.msg_no}")  # Insert message number
        print(f"[Gen][OUT]: {self.msg_no}")
        return msg

    def int_trans(self):
        """
        Handles internal transitions based on the current state.
        """
        if self._cur_state == "Generate":
            self._cur_state = "Generate"  # Remain in "Generate" state
            self.msg_no += 1  # Increment message number