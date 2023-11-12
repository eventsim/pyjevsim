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
from pyjevsim.executor_snapshot_manager import ExecutorSnapshotManager


from pyjevsim.snapshot_executor import SnapshotExecutor
from pyjevsim.model_snapshot_manager import ModelSnapshotManager

from .model_work import WorkModel
from .model_env import ENVModel
from .model_rest import RestModel

def execute_simulation(t_resol=1, execution_mode=ExecutionType.R_TIME):
    # System Executor Initialization
    
    env_data = {"site_id" : 1, "humid" :0.65, "wind" : 1, "temp" : 27, "wbgt" : 27}
    human_data = {"human_id" : "human5", "work_point" : 0, "health_score" : 70, "work_speed" : 2} 
    
    executor_snapshot = ExecutorSnapshotManager()
    
 
    # Model Creation
    env = ENVModel("Env", env_data)
    work = WorkModel("Work")
    rest = RestModel("Rest")

    
    se = SysExecutor(t_resol, ex_mode=execution_mode)
    se.insert_input_port("start")


    # Register Model to Engine
    se.register_entity(env)
    se.register_entity(work)
    se.register_entity(rest)

    # Set up relation among models
    se.coupling_relation(se, "start", env, "process")
    se.coupling_relation(env, "work", work, "work")
    se.coupling_relation(env, "rest", rest, "rest")
    
    se.coupling_relation(work, "process", env, "process")
    se.coupling_relation(work, "rest", rest, "rest")
    
    
    se.coupling_relation(rest, "process", env, "process")
    se.coupling_relation(rest, "keep_rest", rest, "rest")
    
    # Inject External Event to Engine
    
    se.insert_external_event("start", human_data)

    for i in range(20):
        print("simulation time : ", se.get_global_time())
        se.simulate(1)
        if se.get_global_time() == 10 :
            with open("./snapshot/executor/engine10.simx", "wb") as f :
                f.write(executor_snapshot.snapshot_executor(se))
                
                print("sim time 10 : engien snapshot")
                print(se.get_model("Work").human)
            



# Test Suite
def test_casual_order1(capsys):
    execute_simulation(1, ExecutionType.V_TIME)
    #captured = capsys.readouterr()
    print(capsys)