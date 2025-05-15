"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Simple BankSimulation example. 

The User Generator Model generates a Bank User periodically.
The Bank Accountatnt handles the Bank User's operations,
Bank Queue stores the Bank User's data and passes the Bank User's information to the Bank Accountant when no Bank Accountant is available. 

Usage:
In a terminal in the parent directory, run the following command.

   pytest -s ./test_banksim/banksim_classic.py 
"""
import time
import contexts

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor

from examples.banksim.model.model_banksim import Banksim

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    ss = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=None)
        
    stm = Banksim("banksim")

    ss.register_entity(stm)           
    ## Model Relation
    ss.insert_input_port('start')   
    ss.insert_external_event('start', None)

    ## simulation run  
    for i in range(10):
        #print("[time] : ", i)
        ss.simulate(1)
        #print()
        
start_time = time.time()
execute_simulation(1, ExecutionType.V_TIME)
end_time = time.time()
execution_time = end_time - start_time
    