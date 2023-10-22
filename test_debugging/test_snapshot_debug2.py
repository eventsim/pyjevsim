#!/usr/bin/env python

# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

import math
import time

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor

from .model_msg_recv import MsgRecv
from .model_peg import PEG


from pyjevsim.snapshot_executor import SnapshotExecutor
from pyjevsim.model_snapshot_manager import ModelSnapshotManager

from pyjevsim.executor_snapshot_manager import ExecutorSnapshotManager

import os


class DebugSnapshotExecutor(SnapshotExecutor) :
    @staticmethod
    def create_executor(behavior_executor) :
        return DebugSnapshotExecutor(behavior_executor)
    
    def __init__(self, behavior_executor):
        super().__init__(behavior_executor)
        
    def snapshot_time_condition(self, global_time):
        if int(global_time) >= 98 :
            self.snapshot(f"{self.behavior_executor.get_name()}{int(global_time)}")
        print(self.behavior_executor.get_core_model().serialize())
        
    def snapshot(self, name) :
        model_data = self.model_dump()
        
        if model_data : 
            with open(f"./snapshot/model/{name}.simx", "wb") as f :
                f.write(model_data)


def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    # System Executor Initialization
    
    executorsnapshot = ExecutorSnapshotManager()
    snapshot_manager = ModelSnapshotManager()
    
    snapshot_manager.register_snapshot_executor("NewGen", DebugSnapshotExecutor.create_executor)
    
    with open("./snapshot/debugging/se90.simx", "rb") as f :
        engine_data = f.read()
               
    se = executorsnapshot.load_snapshot(engine_data)
    
    se.remove_entity("Gen")
    
    se.set_snapshot_manager(snapshot_manager)
    se.reset_relation()
    
    new_gen = PEG("NewGen")
    
    se.register_entity(new_gen)
    se.coupling_relation(se, "start", new_gen, "start")
    proc = se.get_model("Proc")

    se.coupling_relation(new_gen, "process", proc, "recv")
       

    se.insert_external_event("start", None)

    for i in range(10):
        se.simulate(1)

# Test Suite
def test_casual_order1(capsys):
    execute_simulation(1, ExecutionType.V_TIME)
    #captured = capsys.readouterr()
    desired_output = (
        "[Gen][IN]: started\n[Gen][OUT]: 0\n"
        + "[MsgRecv][IN]: 0\n[Gen][OUT]: 1\n[MsgRecv][IN]: 1\n"
    )
    print(capsys)
    #assert captured.out == desired_output

