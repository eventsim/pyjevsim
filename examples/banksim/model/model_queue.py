"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Banksim Queue Model 
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage

class BankQueue(BehaviorModel):
    """Class representing a bank queue managing users and processors."""

    def __init__(self, name, queue_size, proc_num):
        """
        Args:
            name (str): Name of Model
            queue_size (int): Maximum size of the queue
            proc_num (int): Number of processors
        """
        BehaviorModel.__init__(self, name)
        self.init_state("WAIT")                 # Initialize initial state
        self.insert_state("WAIT", Infinite)     # Add "WAIT" state
        self.insert_state("SEND", 0)            # Add "SEND" state with duration 0
        self.insert_state("DROP", 0) 
        
        self.insert_input_port("user_in")       # Add input port "user_in"
        self.insert_input_port("proc_checked")  # Add input port "proc_checked"

        self.usable_proc = []                   # List of usable processors
        
        for i in range(proc_num):
            self.insert_output_port(f"proc{i}") # Add output port for each processor
            self.usable_proc.append(f"proc{i}") # Add processor to usable list
        self.insert_output_port("result")

        self.proc_num = proc_num                # Number of processors
        self.queue_size = queue_size            # Maximum queue size
        self.user = []                          # List of users in the queue
        self.dropped_user = []
        
    def set_queue_size(self, queue_size):
        """
        Sets the maximum size of the queue.

        Args:
            queue_size (int): Maximum size of the queue
        """
        self.queue_size = queue_size

    def ext_trans(self, port, msg):
        """
        Handles external transitions based on the input port.

        Args:
            port (str): The port that received the message
            msg (SysMessage): The received message
        """
        _time = self.global_time
        if port == "user_in":
            if len(self.user) < self.queue_size:
                user = msg.retrieve()[0]
                self.user.append(user)  # Add user to the queue
                #print(f"[Q][in] ID:{user.get_id()} Time:{_time}")
                self._cur_state = "SEND"
            else:
                user = msg.retrieve()[0]
                #print(f"User Dropped: {user}")
                self._cur_state = "DROP"
                user.set_drop_time(self.global_time)
                self.dropped_user.append(user)

        elif port == "proc_checked":
            #print("proc_checked")
            self.usable_proc.append(msg.retrieve()[0])  # Add processor to usable list
            self._cur_state = "SEND"

        if not self.usable_proc or not self.user:
            self._cur_state = "WAIT"  # Transition to "WAIT" state if no users or processors

    def output(self, msg_deliver):
        """
        Generates the output message when in the "SEND" state.

        Returns:
            SysMessage: The output message
        """
        msg = None
        _time = self.global_time
        if self._cur_state == "SEND":
            user = self.user.pop(0)  # Get the first user in the queue
            #print(f"[Q][out] ID:{user.get_id()} Time:{_time}")
            
            msg = SysMessage(self.get_name(), self.usable_proc.pop(0))
            msg.insert(user)  # Insert user into message
            
            msg2 = SysMessage(self.get_name(), "result")
            msg2.insert(self.dropped_user)
            self.dropped_user = []
            
            msg_deliver.insert_message(msg)
            msg_deliver.insert_message(msg2)
        
        if self._cur_state == "DROP":
            #user = self.user.pop(0)  # Get the first user in the queue
            #print(f"[Q][out] Dropped")
            
            msg = SysMessage(self.get_name(), "result")
            #msg.insert(user)  # Insert user into message
            drop_user = self.dropped_user
            msg.insert(drop_user)
            self.dropped_user = []
            msg_deliver.insert_message(msg)

        return msg_deliver

    def int_trans(self):
        """Handles internal transitions based on the current state."""
        if self._cur_state == "SEND":
            self._cur_state = "SEND"  # Remain in "SEND" state
        if self._cur_state == "DROP" : 
            self._cur_state = "SEND"
        if not self.usable_proc or not self.user:
            self._cur_state = "WAIT"  # Transition to "WAIT" state if no users or processors

    def set_proc_num(self, proc_num):
        """
        Sets the number of processors and adjusts the usable processor list.

        Args:
            proc_num (int): Number of processors
        """
        if proc_num > self.proc_num:
            for i in range(self.proc_num, proc_num):
                self.insert_output_port(f"proc{i}")
                self.usable_proc.append(f"proc{i}")
        elif proc_num < self.proc_num:
            for i in range(proc_num, self.proc_num):
                self.usable_proc.remove(f"proc{i}")

        self.proc_num = proc_num
        #while len(self.user) > self.queue_size:
        #    print(f"User Dropped: {self.user.pop()}")

    def __str__(self):
        """Returns a string representation of the BankQueue.

        Returns:
            str: String representation
        """
        return f">> {self.get_name()}, State:{self._cur_state}, {self.user}"