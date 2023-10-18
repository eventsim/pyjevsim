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

import dill

def debug(engine, global_time, snapshot_cycle) :
    if int(global_time) % snapshot_cycle == 0 :
        engine_info = engine.model_snapshot()
        return dill.dumps(engine_info)
    return None

class DebugingSnapshotBehaviorExecutor(SnapshotExecutor) :
    @staticmethod
    def create_executor(behavior_executor) :
        return DebugingSnapshotBehaviorExecutor(behavior_executor)
    
    def __init__(self, behavior_executor):
        super().__init__(behavior_executor)
    
    def snapshot_time_condition(self, global_time):
        if int(global_time) % 10 == 1 :
            self.snapshot(f"{self.behavior_executor.get_name()}{int(global_time)}")
        pass

    def snapshot(self, name):
        model_data = self.model_dump()
        
        if model_data :
            with open(f"./snapshot/{name}.simx", "wb") as f :
                f.write(model_data)
    
def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    # System Executor Initialization
    
    snapshot_manager = ModelSnapshotManager()
    snapshot_manager.register_snapshot_executor("Gen", DebugingSnapshotBehaviorExecutor.create_executor) 
    #register snapshot executor ## 함수 명 변경 필요
    snapshot_manager.register_snapshot_executor("Proc", DebugingSnapshotBehaviorExecutor.create_executor) 
    # load 하는 부분이 load snapshot-> 모델 이름 : simx를 같이 넣어주면 
    
    
    se = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=snapshot_manager)
    se.insert_input_port("start")

    # Model Creation
    gen = PEG("Gen")
    #snapshot manager : restore entity
    #gen = snapshotmanager.restore_entity("Gen")
    proc = MsgRecv("Proc")
    
    ##특정 시점으로 복원하는 경우 : 시뮬레이션 system executor를 복원하는 경우 -> 내부 모델을 바꿈
    ## 메타정보로 entity 정보 
    
    ## system executor 
    ## 저장 기능을 다 빼고 실행 가능하도록 
    ## snapshot manager가 engine의 정보를 취득하고  

    # Register Model to Engine
    se.register_entity(gen)
    se.register_entity(proc)
    ## 모델 복원시 이름만 : str type으로 들어올 경우 snapshot manager의 factory로 넘기고
    ## behavior model type일 경우 기존과 동일 

    # Set up relation among models
    se.coupling_relation(se, "start", gen, "start")
    se.coupling_relation(gen, "process", proc, "recv")

    # Inject External Event to Engine
    se.insert_external_event("start", None)

    for i in range(100):
        se.simulate(1)
        test = debug(se, se.get_global_time(), 10)
        if test != None :
            with open(f"./snapshot/debug/engine_{i}.simx", "wb") as f :
                f.write(test)

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


