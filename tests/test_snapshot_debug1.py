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

from pyjevsim.executor_snapshot_manager import ExecutorSnapshotManager

  
def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    # System Executor Initialization
    executorsnapshot = ExecutorSnapshotManager()

      
    se = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=None)
    se.insert_input_port("start")

    # Model Creation
    gen = PEG("Gen")
    proc = MsgRecv("Proc")
    
    # Register Model to Engine
    se.register_entity(gen)
    se.register_entity(proc)

    # Set up relation among models
    se.coupling_relation(se, "start", gen, "start")
    se.coupling_relation(gen, "process", proc, "recv")

    # Inject External Event to Engine
    se.insert_external_event("start", None)

    for i in range(100):
        se.simulate(1)
        if i % 30 == 0 :
            with open(f"snapshot/executor/se{i}.simx", "wb") as f :
                f.write(executorsnapshot.snapshot_executor(se))
        
  
# Test Suite
def test_execution_mode(capsys):
    execute_simulation(1, ExecutionType.V_TIME)
    #captured = capsys.readouterr()
    desired_output = (
        "[Gen][IN]: started\n[Gen][OUT]: 0\n"
        + "[MsgRecv][IN]: 0\n[Gen][OUT]: 1\n[MsgRecv][IN]: 1\n"
    )
    print(capsys)
    #assert captured.out == desired_output


