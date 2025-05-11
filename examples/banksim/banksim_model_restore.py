"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Example of restoring a snapshot BankGenerator model to configure a bank simulation.

First, run banksim_model_snapshot.py before proceeding.

The User Generator Model generates a Bank User periodically.
The Bank Accountatnt handles the Bank User's operations,
Bank Queue stores the Bank User's data and passes the Bank User's information to the Bank Accountant when no Bank Accountant is available. 

Usage:
In a terminal in the parent directory, run the following command.

   pytest -s ./test_banksim/banksim_model_restore.py 
"""
import time
import contexts

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor
from pyjevsim.snapshot_manager import SnapshotManager
from pyjevsim.restore_handler import RestoreHandler

from examples.banksim.model_queue import BankQueue
from examples.banksim.model_accountant import BankAccountant

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):    
    snapshot_manager = SnapshotManager(restore_handler=RestoreHandler()) 
    #Restored via Snapshotmanager
    #Specifying restore_handler in Snapshot Manager when restoring a model
    
    ss = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=None)
    
    #case 1 gen 10          
    #case 2 gen 5
    #case 3 gen 15
    gen_num = 15             #Number of BankUserGenerators 
    queue_size = 100         #BankQueue size(reset queue size)
    proc_num = 30           #Number of BankAccountant
    #gen_cycle = 2           #BankUser Generattion cycle(reset cycle)
    
    max_simtime = 10000000

    ## model restore & set register entity
    #BankUserGenerator Restore
    gen_list = []
    for i in range(gen_num) :
        #BankUserGenerator Restore
        with open(f"./snapshot/[time]gen0.simx", "rb") as f :
            gen = snapshot_manager.load_snapshot(f"gen{i}", f.read()) #restore model
        
        #Modification Model Parameter
        #gen cycle set
        #gen.set_cycle(gen_cycle)
        gen_list.append(gen)
        ss.register_entity(gen)    
       
    que = BankQueue('Queue', queue_size, proc_num)
    
    #queue size set
    que.set_queue_size(queue_size)
    que.set_proc_num(proc_num)
    ss.register_entity(que)


    with open(f"./snapshot/[time]result.simx", "rb") as f :
        result = snapshot_manager.load_snapshot(f"result", f.read()) #restore model   
    ss.register_entity(result)

     
    account_list = []
    for i in range(proc_num) :
        account = BankAccountant(f'processor{i}', i)
        account_list.append(account)
        ss.register_entity(account)
        
    ## Model Relation
    for gen in gen_list : 
        ss.coupling_relation(None, 'start', gen, 'start')
        ss.coupling_relation(gen, 'user_out', que, 'user_in')
    ss.coupling_relation(que, "result", result, "drop")
    for i in range(proc_num) : 
        ss.coupling_relation(que, f'proc{i}', account_list[i], 'in')
        ss.coupling_relation(account_list[i], 'next', que, 'proc_checked')
        ss.coupling_relation(account_list[i], 'next', result, 'process')
        
    ss.insert_external_event('start', None)
    
    ## simulation run
    for i in range(max_simtime):
        ss.simulate(1)
       

execute_simulation(1, ExecutionType.V_TIME)
