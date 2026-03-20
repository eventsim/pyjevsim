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
        """
        Args:
            name (str): Name of the accountant
            proc_num (int): Processor number for identification
        """
        BehaviorModel.__init__(self, name)

        self.init_state("WAIT")
        self.insert_state("WAIT", Infinite)
        self.insert_state("PROC", 1)

        self.insert_input_port("in")
        self.insert_output_port("next")

        self.proc_num = f"proc{proc_num}"
        self.user = None
        self.proc_user = []

    def ext_trans(self, port, msg):
        if port == "in":
            self.user = msg.retrieve()[0]
            self._cur_state = "PROC"
            self.update_state("PROC", self.user.get_service_time())

    def output(self, msg_deliver):
        if self._cur_state == "PROC":
            cur_time = self.global_time
            self.user.calc_wait_time(cur_time)
            self.proc_user.append(self.user)

            msg = SysMessage(self.get_name(), "next")
            msg.insert(self.proc_num)
            msg_deliver.insert_message(msg)

    def int_trans(self):
        if self._cur_state == "PROC":
            self._cur_state = "WAIT"
