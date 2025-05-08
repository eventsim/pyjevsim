"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Banksim User Generator Model 
"""
import os
from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
import time

class BankResult(BehaviorModel):
    """A Model representing a bank user generator."""

    def __init__(self, name, max_user):
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
        self.insert_state("STOP", Infinite)
        
        self.insert_input_port("process")  # Add input port "process"
        self.insert_input_port("drop")  # Add input port "drop"

        self.max_user = max_user  # Maximum number of users to generate
        #self.proc_time = proc_time  # Processing time for each user
        self.user_count = 0
        self.user = []
        self.drop_user = []
        self.drop_user_count = 0
        self.start_time = time.time()
        
    def ext_trans(self, port, msg):
        """
        Handles external transitions based on the input port.

        Args:
            port (str): The port that received the message
            msg (SysMessage): The received message
        """
        if port == "process":
            _user = msg.retrieve()[1]
            self.user.append(_user)
            self.user_count += 1
            if self.user_count >= self.max_user :
                self.get_result()
                os._exit(0)
        if port == "drop" :
            drop_user_list = msg.retrieve()[0]
            for _user in drop_user_list : 
                self.drop_user.append(_user)
                self.drop_user_count += 1

    def output(self, msg_deliver):
        pass

    def int_trans(self):
        pass
        
    def get_result(self) :
        print("[BANKSIM RESULT]")
        end_time = time.time()
        print("- Run time : ", end_time - self.start_time)
        print("- Accountant user : ", self.user_count)
        print("- Dropped user : ", self.drop_user_count)
        
        print("\n [Accountant user list]")
        for user in self.user :
            print(user.__str__())
        print("\n [Dropped user list]")
        for drop_user in self.drop_user :
            print(drop_user.__str__())