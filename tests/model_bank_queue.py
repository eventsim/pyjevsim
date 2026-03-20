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
        self.init_state("WAIT")
        self.insert_state("WAIT", Infinite)
        self.insert_state("SEND", 0)

        self.insert_input_port("user_in")
        self.insert_input_port("proc_checked")

        self.usable_proc = []

        for i in range(proc_num):
            self.insert_output_port(f"proc{i}")
            self.usable_proc.append(f"proc{i}")

        self.proc_num = proc_num
        self.queue_size = queue_size
        self.user = []

    def ext_trans(self, port, msg):
        if port == "user_in":
            if len(self.user) < self.queue_size:
                user = msg.retrieve()[0]
                self.user.append(user)
            self._cur_state = "SEND"
        elif port == "proc_checked":
            self.usable_proc.append(msg.retrieve()[0])
            self._cur_state = "SEND"

        if not self.usable_proc or not self.user:
            self._cur_state = "WAIT"

    def output(self, msg_deliver):
        if self._cur_state == "SEND":
            user = self.user.pop(0)
            msg = SysMessage(self.get_name(), self.usable_proc.pop(0))
            msg.insert(user)
            msg_deliver.insert_message(msg)

    def int_trans(self):
        if self._cur_state == "SEND":
            self._cur_state = "SEND"
        if not self.usable_proc or not self.user:
            self._cur_state = "WAIT"
