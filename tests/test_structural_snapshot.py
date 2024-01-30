#!/usr/bin/env python

# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

from pyjevsim.definition import *
from pyjevsim.definition import ExecutionType
from pyjevsim.system_executor import SysExecutor
from .model_stm import STM
from .model_msg_recv import MsgRecv

from pyjevsim.model_snapshot_manager import ModelSnapshotManager
from pyjevsim.snapshot_structural_executor import SnapshotStructuralExecutor

class TestStructuralSnapshot(SnapshotStructuralExecutor) : 
    @staticmethod
    def create_executor(structural_executor) :
        return TestStructuralSnapshot(structural_executor)
    
    def __init__(self, structural_executor):
        super().__init__(structural_executor)
        
    def snapshot_time_condition(self, global_time):
        if global_time % 2 == 0: 
            self.snapshot(f"STM{global_time}") 
    
    def snapshot(self, name) :
        model_data = self.model_dump()
        
        if model_data :
            with open(f"./snapshot/STM/{name}.simx", "wb") as f :
                f.write(model_data)
    

def test_f():
    
    snapshot_manager = ModelSnapshotManager()
    
    gen = STM("STM")
    mr = MsgRecv("MsgRecv")
    
    snapshot_manager.register_snapshot_executor("STM", TestStructuralSnapshot.create_executor)
    
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=snapshot_manager)
    se.insert_input_port("start")


    se.register_entity(gen)
    se.register_entity(mr)

    se.coupling_relation(se, "start", gen, "start")
    se.coupling_relation(gen, "output", mr, "recv")

    se.insert_external_event("start", None)
    se.simulate(10)
    print(se.port_map)

    
    #assert mr.msg_recv > 0