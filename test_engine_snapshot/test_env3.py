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
    
    executor_snapshot = ExecutorSnapshotManager()
    with open("./snapshot/executor/engine10.simx", "rb") as f :
        se = executor_snapshot.load_snapshot(f.read())
    
    se.get_model("Env").human["work_speed"] = 3
    
    print()
    print(se.get_model("Env").human)

    for i in range(70):
        print("simulation time : ", se.get_global_time())
        se.simulate(1)

    print(se.get_model("Env").human)

# Test Suite
def test_casual_order1(capsys):
    execute_simulation(1, ExecutionType.V_TIME)
    #captured = capsys.readouterr()
    print(capsys)