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

from .model_bank_user import BankUser


class BankUserGenerator(BehaviorModel):
    """A Model representing a bank user generator."""

    def __init__(self, name, cycle, max_user, proc_time):
        """
        Args:
            name (str): Name of Model
            cycle (float): Generation cycle time
            max_user (int): Maximum number of users to generate
            proc_time (float): Processing time for each user
        """
        BehaviorModel.__init__(self, name)
        self.init_state("WAIT")
        self.insert_state("WAIT", Infinite)
        self.insert_state("GEN", cycle)

        self.insert_input_port("start")
        self.insert_output_port("user_out")

        self.cycle = cycle
        self.generated_user = 0
        self.max_user = max_user
        self.proc_time = proc_time

    def ext_trans(self, port, msg):
        if port == "start":
            self._cur_state = "GEN"

    def output(self, msg_deliver):
        _time = self.global_time
        msg = SysMessage(self.get_name(), "user_out")
        bu = BankUser(f"{self.get_name()}-{self.generated_user}", self.proc_time)
        bu.set_arrival_time(_time)
        msg.insert(bu)
        self.generated_user += 1
        msg_deliver.insert_message(msg)

    def int_trans(self):
        if self._cur_state == "GEN" and self.generated_user >= self.max_user:
            self._cur_state = "WAIT"
        else:
            self.update_state("GEN", self.cycle)

    def set_cycle(self, cycle):
        self.cycle = cycle

    def get_user(self):
        return self.max_user - self.generated_user
