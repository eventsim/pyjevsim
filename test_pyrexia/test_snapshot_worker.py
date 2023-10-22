#!/usr/bin/env python

# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

import math
import time

from pyjevsim.definition import *
from pyjevsim.snapshot_executor import SnapshotExecutor
from pyjevsim.model_snapshot_manager import ModelSnapshotManager
from pyjevsim.system_executor import SysExecutor

from .model_worker import WorkerManager
from .model_env import ENV

class ModelSnapshotExecutor(SnapshotExecutor) :
    @staticmethod
    def create_executor(behavior_executor) :
        return ModelSnapshotExecutor(behavior_executor)
    
    def __init__(self, behavior_executor):
        super().__init__(behavior_executor)
    

    def snapshot_pre_condition_ext(self, port, msg, cur_state):
        if msg.retrieve()[0]["health_score"] <= 10 : 
            self.snapshot(f"{self.behavior_executor.get_name()}_low_health")
            

    def snapshot(self, name) :
        model_data = self.model_dump()
        if model_data : 
            with open(f"./snapshot/test_pyrexia/{name}.simx", "wb") as f :
                f.write(model_data)

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    # System Executor Initialization
    
    env_data = {"site_id" : 1, "humid" :0.65, "wind" : 1, "temp" : 27, "wbgt" : 27}
    human_data = {"human_id" : 30221045, "gender" : 0, "age" : 26, "daily_condition" : 0, "medical_history" : 0, "health_score" : 8}
    
    # Model Creation
    env = ENV("Env", env_data)
    worker = WorkerManager("Worker")
    
    snapshot_manager = ModelSnapshotManager() 
    snapshot_manager.register_snapshot_executor("Worker", ModelSnapshotExecutor.create_executor)
    
    se = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=snapshot_manager)
    se.insert_input_port("start")


    # Register Model to Engine
    se.register_entity(env)
    se.register_entity(worker)

    # Set up relation among models
    se.coupling_relation(se, "start", worker, "worker_check")
    
    se.coupling_relation(worker, "process", env, "env_check")
    se.coupling_relation(env, "human_check", worker, "worker_check")

    # Inject External Event to Engine
    se.insert_external_event("start", human_data)

    for _ in range(3):
        se.simulate(1)


# Test Suite
def test_casual_order1(capsys):
    execute_simulation(1, ExecutionType.V_TIME)
    captured = capsys.readouterr()
    print(captured)