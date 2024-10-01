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

from pyjevsim.definition import *
from pyjevsim.snapshot_manager import SnapshotManager

from .model_accountant import BankAccountant

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):   

    snapshot_manager = SnapshotManager(t_resol, ex_mode=execution_mode, name = "banksim", path = "./snapshot")   
    ss = snapshot_manager.get_engine() #Restore a snapshot simulation


    ss.insert_input_port('start')

    ## Adding a new model to an existing simulation
    ## Increase the number of processes
    que = ss.get_model('Queue')
    que.set_proc_num(8)
    for i in (5, 6, 7) :
        account = BankAccountant(f'processor{i}', i)
        ss.register_entity(account)
        
        ss.coupling_relation(que, f'proc{i}', account, 'in')
        ss.coupling_relation(account, 'next', que, 'proc_checked')
    
    
    ss.insert_external_event('start', None)
    
    ## simulation run
    for _ in range(25000):
        print()
        ss.simulate(1)
        
def test_casual_order1(capsys):
    execute_simulation(1, ExecutionType.V_TIME)
    print(capsys)
    