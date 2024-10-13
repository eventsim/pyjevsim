"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains an object SnapshotExecutor that decorates a BehaviorExecutor to snapshot a BehaviorModel. 
"""
import dill
import os

from .executor import Executor
from .snapshot_condition import SnapshotCondition

class SnapshotExecutor(Executor):
    """
    Framework for adding snapshot conditions to behavior models.
    It is a decorated form of BehaviorExecutor, 
    inheriting from that class and entering snapshot conditions. 
    The snapshot condition can be before or after a function in the behavior model.  
    """
    def __init__(self, behavior_executor, condition):
        """
        Args:
            behavior_executor (BehaviorExecutor): BehaviorExecutor to decorate
        """
        Executor.__init__(self,
                         behavior_executor.get_create_time(),
                         behavior_executor.get_destruct_time(),
                         behavior_executor.get_engine_name())        
        
        self.behavior_executor = behavior_executor
        self.condition = condition

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
        if self.condition.snapshot_pre_condition_ext(port, msg, self.get_cur_state()):
            self.snapshot("ext_before")
        #Conditions created before ext_trans function 
        self.behavior_executor.ext_trans(port, msg)
        if self.condition.snapshot_post_condition_ext(port, msg, self.get_cur_state()):
            self.snapshot("ext_after")
        #Conditions generated after ext_trans function 

    # Internal Transition
    def int_trans(self):
        """Handles the internal transition."""
        if self.condition.snapshot_pre_condition_int(self.get_cur_state()):
            self.snapshot("int_before")
        #Conditions created before int_trans function 
        self.behavior_executor.int_trans()
        if self.condition.snapshot_post_condition_int(self.get_cur_state()):
            self.snapshot("int_after")
        #Conditions generated after int_trans function

    # Output Function
    def output(self):
        """Handles the output function.

        Returns:
            Message: The output message
        """
        if self.condition.snapshot_pre_condition_out(self.get_cur_state()):
            self.snapshot("output_before")
        #Conditions created before output function 
        out_msg = self.behavior_executor.output()
        if self.condition.snapshot_post_condition_out(self.get_cur_state(), out_msg):
            self.snapshot("output_after")
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
        if self.condition.snapshot_time_condition(global_time):
            self.snapshot("time")
        #Snapshot conditions over time
        self.behavior_executor.set_req_time(global_time)

    def get_req_time(self):
        """Returns the request time.
        
        Returns:
            float: Request time
        """
        return self.behavior_executor.get_req_time()

    def snapshot(self, _prefix, _path="./snapshot"):
        """An abstract method that creates a method to take a snapshot.
        You can use the snapshot method in a conditional method.
        Use the model_dump method to get the model data in bytes. 
        Save that data to the DB or save it to a file.

        Args:
            name (str): The name of the snapshot
        """
        model_data = self.model_dump() #model snapshot data(binary type)
        
        ## snapshot model to simx file (path : ./snapshot/model.simx)  
        if model_data : 
            if not os.path.exists(_path):
                os.makedirs(_path)
                
            with open(f"{_path}/[{_prefix}]{self.behavior_executor.get_name()}.simx", "wb") as f :
                f.write(model_data)

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