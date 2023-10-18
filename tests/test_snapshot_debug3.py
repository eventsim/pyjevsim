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

from pyjevsim.snapshot_manager import ModelSnapshotManager

import dill
import os

def load_last_engine(path) : 
    file_list = os.listdir(path)
    return path + file_list[-1]
  
def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    # System Executor Initialization
    
    snapshot_manager = ModelSnapshotManager()
    
    with open(load_last_engine("./snapshot/debug/"), "rb") as f :
        engine_data = f.read()
        
    se = snapshot_manager.engine_load(engine_data)

    for i in range(30):
        se.simulate(1)
        #model executor
        #모든 모델 저장아니고 필요한 모델만 dump
        #사용자가 필요한 모델을 dump함 
        #우리는 과정만 제공하고 automatic debugging을 할 수 있다만 
        #어떤 형태를 날지 기술만 해주도록
        #사용 시나리오 
        #motivation error 나는 모델 
        
        #error 모델 : banksim 수정해서 오류나도록 link 빼고
        #한쪽만 연결 
        #buffer는 두고
        #마지막 processor에서 연결x -> 반대로 추적해서 debug과정 
        
        #load할 경우 debug point가 어떻게 바뀌는지 
        #어떻게? 어느 시점에? 어느 위치? -> snapshot point를 어떻게 설명해야할지
        

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

