"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Usage:
In a terminal in the parent directory, run the following command.

   pytest -s ./test_hierachical/banksim.py 
"""
import time

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor

from .model_banksim import STM

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    ss = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=None)
        
    model = STM("banksim") 
    ## Model Relation
    ss.insert_input_port('start')

    ss.register_entity(model)
    
    ss.coupling_relation(None, 'start', model, 'start')
    ss.insert_external_event('start', None)

    print(ss.port_map)

    ## simulation run  
    for i in range(100):
        print("[time] : ", i)
        ss.simulate(1)
        
start_time = time.time()
execute_simulation(1, ExecutionType.V_TIME)
end_time = time.time()
execution_time = end_time - start_time
print(f"run time: {execution_time} sec")
    