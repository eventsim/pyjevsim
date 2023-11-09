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
    
    engine_snapshot = ExecutorSnapshotManager()
    
    with open("./snapshot/debug/executor21.simx", "rb") as f :
        engine_data = f.read()    
    
    se = engine_snapshot.load_snapshot(engine_data)
    
    env = se.get_model("Env")
    rest = se.get_model("Rest")
    se.coupling_relation(rest, "process", env, "process")
    se.coupling_relation(rest, "keep_rest", rest, "rest")
    
    for i in range(30):
        print("simulation time : ", se.get_global_time())
        se.simulate(1)


# Test Suite
def test_casual_order1(capsys):
    execute_simulation(0.5, ExecutionType.R_TIME)
    #captured = capsys.readouterr()
    print(capsys)