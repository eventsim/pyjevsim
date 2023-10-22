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
from pyjevsim.system_message import SysMessage

from .model_worker import WorkerManager
from .model_env import ENV


def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    # System Executor Initialization
    se = SysExecutor(t_resol, ex_mode=execution_mode)
    se.insert_input_port("start")

    env_data = {"humidity" : 32, "wind" : 14.7, "temps" : 35.2, "datetime" : 10, "wbgt" : 12.1}
    human_data = {"human_id" : 30221045, "smoke" : "S", "work_intensive" : 1, "time_stamp" : 10}
    
    # Model Creation
    env = ENV("Env", env_data)
    worker = WorkerManager("Worker")

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