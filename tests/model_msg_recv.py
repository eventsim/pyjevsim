"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""
""" This module contains Message Receive Model """

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage

class MsgRecv(BehaviorModel):
    """Message Receiver Model that handles simulation events."""

    def __init__(self, name):
        """
        Args:
            name (str): The name of the message receiver
        """
        BehaviorModel.__init__(self, name)

        self.init_state("Wait")                 # Initialize initial state
        self.insert_state("Wait", Infinite)     # Add "Wait" state
        self.insert_input_port("recv")          # Add input port "recv"

        self.msg_recv = 0                       # Initialize message received count

    def ext_trans(self, port, msg):
        """
        Handles external transitions based on the input port.

        Args:
            port (str): The port that received the message
            msg (SysMessage): The received message
        """
        if port == "recv":
            self._cur_state = "Wait"  # Remain in "Wait" state
            data = msg.retrieve()  # Retrieve message data
            print(f"[MsgRecv][IN]: {data[0]}")  # Print received message
            self.msg_recv += 1  # Increment received message count

    def output(self):
        """No output function for MsgRecv."""
        return None

    def int_trans(self):
        """Handles internal transitions based on the current state."""
        if self._cur_state == "Wait":
            self._cur_state = "Wait"  # Remain in "Wait" state