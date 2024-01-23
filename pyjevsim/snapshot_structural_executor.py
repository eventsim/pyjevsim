import copy
from collections import deque

from .definition import Infinite
from .executor import Executor

import dill

from abc import abstractmethod, abstractstaticmethod


class SnapshotStructuralExecutor(Executor):
    @abstractstaticmethod
    def create_executor(cls, structural_executor):
        return SnapshotStructuralExecutor(structural_executor) ##class create
    
    def __init__(
        self, structural_executor
    ):
        super().__init__(structural_executor.get_global_time(),
                         structural_executor.get_create_time(),
                         structural_executor.get_destruct_time(),
                         structural_executor.get_engine_name(),
                         structural_executor.get_core_model(),
                         structural_executor.get_creator_functor())
        
        self.structural_executor = structural_executor

    def get_core_model(self):
        return self.structural_executor.get_core_model()

    # @abstractmethod
    def init_executor(self):
        self.structural_executor.init_executor()

    def get_name(self):
        return self.structural_executor.get_name()
        
    def get_engine_name(self):
        return self.structural_executor.get_engine_name()

    def set_engine_name(self, engine_name):
        self.structural_executor.set_engine_name(engine_name)

    def get_create_time(self):
        return self.structural_executor.get_create_time()

    def get_destruct_time(self):
        return self.structural_executor.get_destruct_time()

    def get_obj_id(self):
        return self.structural_executor.get_obj_id()

    
    @abstractmethod
    def snapshot_time_condition(self, global_time):
        pass
        
    @abstractmethod
    def snapshot_pre_condition_int(self, cur_state):
        pass
    
    @abstractmethod
    def snapshot_post_condition_int(self,cur_state):
        pass
    
    @abstractmethod
    def snapshot_pre_condition_out(self, cur_state):
        pass
    
    @abstractmethod
    def snapshot_post_condition_out(self, msg, cur_state):
        pass
    
    @abstractmethod
    def snapshot(self, name) :
        pass

    # External Transition
    def ext_trans(self, port, msg):
        self.structural_executor.ext_trans(port, msg)

    # Internal Transition
    def int_trans(self):
        self.structural_executor.int_trans()
        
    def message_handling(self, obj, msg):
        self.structural_executor.message_handling(obj, msg)
        
    def output_event_handling(self, obj, msg):
        self.structural_executor.output_event_handling(obj, msg)

    # Output Function
    def output(self):
        self.structural_executor.output()
        
    def set_req_time(self, global_time):
        self.structural_executor.set_req_time(global_time)

    def get_req_time(self):
        return self.structural_executor.get_req_time()
    
    def model_dump(self) : 
        return dill.dumps(self.structural_executor.get_core_model().model_snapshot())
    
    def get_structural_executor(self) :
        return self.structural_executor