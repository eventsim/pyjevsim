"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Example of restoring Simulation snapshot to configure a bank simulation.

First, run banksim_snapshot.py before proceeding.

The User Generator Model generates a Bank User periodically.
The Bank Accountatnt handles the Bank User's operations,
Bank Queue stores the Bank User's data and passes the Bank User's information to the Bank Accountant when no Bank Accountant is available. 

Usage:
In a terminal in the parent directory, run the following command.

   pytest -s ./test_banksim/banksim_restore.py 
"""
import time

from pyjevsim.definition import *
from pyjevsim.snapshot_manager import SnapshotManager
from pyjevsim.restore_handler import RestoreHandler

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):   
    clssic_gen_num = 10             #Number of BankUserGenerators
    gen_cycle = 1           #BankUser Generattion cycle
    max_simtime = 90000    #simulation time
    
    snapshot_time = 10000
    
    restore_handler = RestoreHandler(1, ex_mode=ExecutionType.V_TIME, name = f"banksim{snapshot_time}", path = "./snapshot")
    snapshot_manager = SnapshotManager(restore_handler)   
    ss = snapshot_manager.get_engine() #Restore a snapshot simulation


    ss.insert_input_port('start')

    ## Adding a new model to an existing simulation
    
    for i in range(clssic_gen_num) : 
        gen = ss.get_model(f"gen{i}")        
        gen.set_cycle(gen_cycle)
    ss.insert_external_event('start', None)

    
    ## simulation run
    for i in range(max_simtime):
        print("[time] : ", i)
        ss.simulate(1)
        
start_time = time.time()
execute_simulation(1, ExecutionType.V_TIME)
end_time = time.time()
execution_time = end_time - start_time
print(f"run time: {execution_time} sec")