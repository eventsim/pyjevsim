"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""
from abc import abstractmethod, abstractstaticmethod

class SnapshotCondition:
    @abstractstaticmethod
    def create_executor(behavior_executor) :
        return SnapshotCondition(behavior_executor)
    
    def __init__(self, behavior_executor):
        self.behavior_executor = behavior_executor
        #super().__init__(behavior_executor) #set behavior_executor
        
    #def __init__(self):
    #    pass
    
    @abstractmethod
    def snapshot_time_condition(self, global_time):
        """Abstract method for snapshot time condition.
        
        Args:
            global_time (float): The global time / simulation time
        """
        return False

    @abstractmethod
    def snapshot_pre_condition_ext(self, port, msg, cur_state):
        """Abstract method for pre-condition of external transition snapshot.

        Args:
            port (str): The port name
            msg (SysMessage): The message
            cur_state (str): The current state
        """
        return False

    @abstractmethod
    def snapshot_post_condition_ext(self, port, msg, cur_state):
        """Abstract method for post-condition of external transition snapshot.

        Args:
            port (str): The port name
            msg (SysMessage): The message
            cur_state (str): The current state
        """
        return False

    @abstractmethod
    def snapshot_pre_condition_int(self, cur_state):
        """Abstract method for pre-condition of internal transition snapshot.

        Args:
            cur_state (str): The current state
        """
        return False

    @abstractmethod
    def snapshot_post_condition_int(self, cur_state):
        """Abstract method for post-condition of internal transition snapshot.
        
        Args:
            cur_state (str): The current state
        """
        return False

    @abstractmethod
    def snapshot_pre_condition_out(self, cur_state):
        """Abstract method for pre-condition of output snapshot.
        
        Args:
            cur_state (str): The current state
        """
        return False

    @abstractmethod
    def snapshot_post_condition_out(self, msg, cur_state):
        """Abstract method for post-condition of output snapshot.
        
        Args:
            msg (SysMessage): The message
            cur_state (str): The current state
        """
        return False