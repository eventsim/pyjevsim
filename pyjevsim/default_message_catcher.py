"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains a default model, DefaultMessageCatcher, for catching uncaught messages. 
"""

from .behavior_model import BehaviorModel
from .definition import *

class DefaultMessageCatcher(BehaviorModel):
    """
    A default model for catching uncaught messages.
    Receiving and not processing uncaught messages.
    """

    def __init__(self, _name):
        super().__init__(_name)

        self.init_state("IDLE")  # Set initial state to 'IDLE'
        self.insert_state("IDLE", Infinite)  # Insert 'IDLE' state with infinite duration
        self.insert_input_port("uncaught")  # Insert 'uncaught' input port

    def ext_trans(self, port, msg):
        """
        Received an uncaught message.
        
        Args:
            port (str): The port name
            msg (SysMessage): The incoming message
        """
        data = msg.retrieve()  # Retrieve message

    def int_trans(self):
        return

    def output(self, msg_deliver):
        return msg_deliver
    