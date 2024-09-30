"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Buffer Model 
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage

class Buffer(BehaviorModel):
    """Buffer model to store simulation events."""

    def __init__(self, name):
        """
        Args:
            name (str): The name of the buffer
        """
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")                 # Initialize initial state
        self.insert_state("Wait", Infinite)     # Add "Wait" state
        self.insert_state("Delay", 0)           # Add "Delay" state

        self.insert_input_port("recv")          # Add input port "recv"
        self.insert_output_port("output")       # Add output port "output"
        self._msg = None                        # Initialize message storage variable

    def ext_trans(self, port, msg):
        """
        Handles external transitions based on the input port.

        Args:
            port (str): The port that received the message
            msg (SysMessage): The received message
        """
        if port == "recv":
            print(f"[Buf][IN]: recv")
            self._msg = msg  # Store message
            self._cur_state = "Delay"  # Transition state to "Delay"

    def output(self):
        """
        Generates the output message when in the "Delay" state.

        Returns:
            SysMessage: The output message
        """
        print(f"[Buf][OUT]: {self._msg.retrieve()[0]}")
        msg = SysMessage(self.get_name(), "output")
        msg.insert(f"{self._msg.retrieve()[0]}")  # Insert message
        return msg

    def int_trans(self):
        """
        Handles internal transitions based on the current state.
        """
        if self._cur_state == "Delay":
            self._cur_state = "Wait"  # Transition state to "Wait"