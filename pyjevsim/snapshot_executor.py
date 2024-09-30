"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""
""" This module contains an object SnapshotExecutor that decorates a BehaviorExecutor to snapshot a BehaviorModel. """

from abc import abstractmethod, abstractstaticmethod
import dill

from .executor import Executor

class SnapshotExecutor(Executor):
    """
    Framework for adding snapshot conditions to behavior models.
    It is a decorated form of BehaviorExecutor, 
    inheriting from that class and entering snapshot conditions. 
    The snapshot condition can be before or after a function in the behavior model.  
    """

    @abstractstaticmethod
    def create_executor(cls, behavior_executor):
        """Creates a SnapshotExecutor instance.

        Args:
            cls (type): Name of created class
            behavior_executor (BehaviorExecutor):BehaviorExecutor to decorate
        Returns:
            SnapshotExecutor: The created snapshot executor
        """
        return SnapshotExecutor(behavior_executor)

    def __init__(self, behavior_executor):
        """
        Args:
            behavior_executor (BehaviorExecutor): BehaviorExecutor to decorate
        """
        super().__init__(behavior_executor.get_create_time(),
                         behavior_executor.get_destruct_time(),
                         behavior_executor.get_engine_name())        
        self.behavior_executor = behavior_executor

    def get_core_model(self):
        """Returns BehaviorModel of SnapshotExecutor.

        Returns:
            CoreModel: BehaviorModel
        """
        return self.behavior_executor.get_core_model()

    def __str__(self):
        """Returns the string representation of SnapshotExecutor.

        Returns:
            str: String representation
        """
        return "SNM" + self.behavior_executor.__str__()

    def get_name(self):
        """Returns the name of SnapshotExecutor.
        
        Returns:
            str: Name
        """
        return self.behavior_executor.get_name()

    def get_engine_name(self):
        """Returns SysExecutor name of SnapshotExecutor.
        
        Returns:
            str: SysExecutor name
        """
        return self.behavior_executor.get_engine_name()

    def set_engine_name(self, engine_name):
        """Sets SysExecutor name of SnapshotExecutor.

        Args:
            engine_name (str): SysExecutor name
        """
        self.behavior_executor.set_engine_name(engine_name)

    def get_create_time(self):
        """Returns the creation time of SnapshotExecutor.

        Returns:
            float: Creation time
        """
        return self.behavior_executor.get_create_time()

    def get_destruct_time(self):
        """Returns the destruction time of SnapshotExecutor.

        Returns:
            float: Destruction time
        """
        return self.behavior_executor.get_destruct_time()

    def get_obj_id(self):
        """Return object ID of SnapshotExecutor.

        Returns:
            int: Object ID
        """
        return self.behavior_executor.get_obj_id()

    # State management
    def get_cur_state(self):
        """Returns the current state of SnapshotExecutor.

        Returns:
            str: Current state 
        """
        return self.behavior_executor.get_cur_state()

    def init_state(self, state):
        """Initializes the state of SnapshotExecutor.

        Args:
            state (str): The state to set / 설정할 상태
        """
        self.behavior_executor.init_state(state)

    # External Transition
    def ext_trans(self, port, msg):
        """Handles the external transition.
        
        Args:
            port (str): The port name
            msg (Message): The message
        """
        self.snapshot_pre_condition_ext(port, msg, self.get_cur_state())
        #Conditions created before ext_trans function 
        self.behavior_executor.ext_trans(port, msg)
        self.snapshot_post_condition_ext(port, msg, self.get_cur_state())
        #Conditions generated after ext_trans function 

    # Internal Transition
    def int_trans(self):
        """Handles the internal transition."""
        self.snapshot_pre_condition_int(self.get_cur_state())
        #Conditions created before int_trans function 
        self.behavior_executor.int_trans()
        self.snapshot_post_condition_int(self.get_cur_state())
        #Conditions generated after int_trans function

    # Output Function
    def output(self):
        """Handles the output function.

        Returns:
            Message: The output message
        """
        self.snapshot_pre_condition_out(self.get_cur_state())
        #Conditions created before output function 
        out_msg = self.behavior_executor.output()
        self.snapshot_post_condition_out(self.get_cur_state(), out_msg)
        #Conditions generated after output function
        
        return out_msg

    # Time Advanced Function
    def time_advance(self):
        """Returns the time advance value.

        Returns:
            float: Time advance value
        """
        return self.behavior_executor.time_advance()

    def set_req_time(self, global_time):
        """Sets the request time.

        Args:
            global_time (float): Simulation time
        """
        self.snapshot_time_condition(global_time)
        #Snapshot conditions over time
        self.behavior_executor.set_req_time(global_time)

    def get_req_time(self):
        """Returns the request time.
        
        Returns:
            float: Request time
        """
        return self.behavior_executor.get_req_time()

    @abstractmethod
    def snapshot_time_condition(self, global_time):
        """Abstract method for snapshot time condition.
        
        Args:
            global_time (float): The global time / simulation time
        """
        pass

    @abstractmethod
    def snapshot_pre_condition_ext(self, port, msg, cur_state):
        """Abstract method for pre-condition of external transition snapshot.

        Args:
            port (str): The port name
            msg (SysMessage): The message
            cur_state (str): The current state
        """
        pass

    @abstractmethod
    def snapshot_post_condition_ext(self, port, msg, cur_state):
        """Abstract method for post-condition of external transition snapshot.

        Args:
            port (str): The port name
            msg (SysMessage): The message
            cur_state (str): The current state
        """
        pass

    @abstractmethod
    def snapshot_pre_condition_int(self, cur_state):
        """Abstract method for pre-condition of internal transition snapshot.

        Args:
            cur_state (str): The current state
        """
        pass

    @abstractmethod
    def snapshot_post_condition_int(self, cur_state):
        """Abstract method for post-condition of internal transition snapshot.
        
        Args:
            cur_state (str): The current state
        """
        pass

    @abstractmethod
    def snapshot_pre_condition_out(self, cur_state):
        """Abstract method for pre-condition of output snapshot.
        
        Args:
            cur_state (str): The current state
        """
        pass

    @abstractmethod
    def snapshot_post_condition_out(self, msg, cur_state):
        """Abstract method for post-condition of output snapshot.
        
        Args:
            msg (SysMessage): The message
            cur_state (str): The current state
        """
        pass

    @abstractmethod
    def snapshot(self, name):
        """An abstract method that creates a method to take a snapshot.
        You can use the snapshot method in a conditional method.
        Use the model_dump method to get the model data in bytes. 
        Save that data to the DB or save it to a file.

        Args:
            name (str): The name of the snapshot
        """
        pass

    def model_dump(self):
        """Dumps BehaviorModel
        
        Returns:
            bytes: The dumped BehaviorModel
        """
        return dill.dumps(self.behavior_executor.get_core_model().model_snapshot())

    def get_behavior_executor(self):
        """Return BehaviorExecutor.

        Returns:
            BehaviorExecutor: The behavior executor / 동작 실행기
        """
        return self.behavior_executor
    