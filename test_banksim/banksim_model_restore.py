"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""
""" 
Example of restoring a snapshot BankGenerator model to configure a bank simulation.

First, run banksim_model_snapshot.py before proceeding.

The User Generator Model generates a Bank User periodically.
The Bank Accountatnt handles the Bank User's operations,
Bank Queue stores the Bank User's data and passes the Bank User's information to the Bank Accountant when no Bank Accountant is available. 

Usage:
In a terminal in the parent directory, run the following command.
pytest -s ./test_banksim/banksim_model_restore.py 
"""

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor
from pyjevsim.model_snapshot_manager import ModelSnapshotManager

from .model_accountant import BankAccountant

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):    
    snapshot_manager = ModelSnapshotManager()
    ss = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=snapshot_manager)
               
    gen_num = 3             #Number of BankUserGenerators 
    queue_size = 10         #BankQueue size(reset queue size)
    proc_num = 5            #Number of BankAccountant
    gen_cycle = 2           #BankUser Generattion cycle(reset cycle)
    
    ## model restore & set register entity
    #BankUserGenerator Restore
    gen_list = []
    for i in range(gen_num) :
        #BankUserGenerator Restore
        with open(f"./snapshot/gen{i}.simx", "rb") as f :
            gen = snapshot_manager.load_snapshot(f"gen{i}", f.read())  
        
        #gen cycle set
        gen.set_cycle(gen_cycle)
    
        gen_list.append(gen)
        ss.register_entity(gen)    
    
    #BankQueue Restore
    with open(f"./snapshot/Queue.simx", "rb") as f :
        que = snapshot_manager.load_snapshot(f"Queue", f.read())
    
    
    #queue size set
    que.set_queue_size(queue_size)
    que.set_proc_num(proc_num)
    ss.register_entity(que)
     
    account_list = []
    for i in range(proc_num) :
        account = BankAccountant(f'processor{i}', i)
        account_list.append(account)
        ss.register_entity(account)
        
    ## Model Relation
    for gen in gen_list : 
        ss.coupling_relation(None, 'start', gen, 'start')
        ss.coupling_relation(gen, 'user_out', que, 'user_in')
    
    for i in range(proc_num) : 
        ss.coupling_relation(que, f'proc{i}', account_list[i], 'in')
        ss.coupling_relation(account_list[i], 'next', que, 'proc_checked')
        
    ss.insert_external_event('start', None)
    
    ## simulation run
    for i in range(25000):
        print()
        ss.simulate(1)
       

def test_casual_order1(capsys):
    execute_simulation(1, ExecutionType.V_TIME)
    print(capsys)
    