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

from pyjevsim.model_snapshot_manager import ModelSnapshotManager

import dill
import os

def load_last_engine(path) : 
    file_list = os.listdir(path)
    return path + file_list[-1]

def debug(engine, global_time, snapshot_cycle) :
    if int(global_time) % snapshot_cycle == 0 :
        engine_info = engine.model_snapshot()
        return dill.dumps(engine_info)
    return None
  
def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    # System Executor Initialization
    
    snapshot_manager = ModelSnapshotManager()
    
    with open(load_last_engine("./snapshot/debug/"), "rb") as f :
        engine_data = f.read()
        
    se = snapshot_manager.engine_load(engine_data)
       
    for i in range(30):
        se.simulate(1)

        test = debug(se, se.get_global_time(), 5)
        if test != None :
            with open(f"./snapshot/debug/engine_{se.get_global_time()}.simx", "wb") as f :
                f.write(test)

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

