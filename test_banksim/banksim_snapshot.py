"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Example of taking a snapshot of the model and model relationships during a bank simulation run.

The User Generator Model generates a Bank User periodically.
The Bank Accountatnt handles the Bank User's operations,
Bank Queue stores the Bank User's data and passes the Bank User's information to the Bank Accountant when no Bank Accountant is available. 

Usage:
In a terminal in the parent directory, run the following command.

   pytest -s ./test_banksim/banksim_snapshot.py 
"""

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor
from pyjevsim.model_snapshot_manager import ModelSnapshotManager

from .model_accountant import BankAccountant
from .model_queue import BankQueue
from .model_user_gen import BankUserGenerator

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):    
    snapshot_manager = ModelSnapshotManager()
    ss = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=snapshot_manager)
    
    gen_num = 3             #Number of BankUserGenerators 
    queue_size = 10         #BankQueue size
    proc_num = 5            #Number of BankAccountant
    
    user_process_time = 3   #BankUser's processing speed
    gen_cycle = 2           #BankUser Generattion cycle
    max_user = 50000        #Total number of users generated
    
    
    ## model set & register entity
    gen_list = []
    user = int(max_user / gen_num)
    for i in range(gen_num) :
        if i == gen_num-1:
            user += max_user % gen_num
        gen = BankUserGenerator(f'gen{i}', gen_cycle, user, user_process_time)
        gen_list.append(gen)
        ss.register_entity(gen)  
            
    que = BankQueue('Queue', queue_size, proc_num)
    ss.register_entity(que)
    
    
    account_list = []
    for i in range(proc_num) :
        account = BankAccountant(f'processor{i}', i)
        account_list.append(account)
        ss.register_entity(account)
        
    ## Model Relation
    ss.insert_input_port('start')

    for gen in gen_list : 
        ss.coupling_relation(None, 'start', gen, 'start')
        ss.coupling_relation(gen, 'user_out', que, 'user_in')
    for i in range(proc_num) : 
        ss.coupling_relation(que, f'proc{i}', account_list[i], 'in')
        ss.coupling_relation(account_list[i], 'next', que, 'proc_checked')
    
    ss.insert_external_event('start', None)
    
    # simulation run
        
    for i in range(100000):        
        # Snapshot when simulation time is 10000 
        if i >= 10000 : 
            ##snapshot at simtime 10000(path ./snapshot/banksim)
            ss.snapshot_simulation(name = "banksim", directory_path = "./snapshot")
            ss.simulation_stop()
            break
        
        ss.simulate(1)
    
execute_simulation(1, ExecutionType.V_TIME)
