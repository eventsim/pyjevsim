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
import contexts

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor

from examples.banksim.model_accountant import BankAccountant
from examples.banksim.model_queue import BankQueue
from examples.banksim.model_user_gen import BankUserGenerator
from examples.banksim.model_result import BankResult

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    ss = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=None)
        
    gen_num = 10            #Number of BankUserGenerators 
    queue_size = 30        #BankQueue size
    proc_num = 30           #Number of BankAccountant
    
    #user_process_time = random.randint(1, 10)   #BankUser's processing speed
    #gen_cycle = 2           #BankUser Generattion cycle
    max_user = 500000        #Total number of users generated
    
    max_simtime = 1000000    #simulation time
    
    
    ## model set & register entity
    gen_list = []
    for i in range(gen_num) :
        gen = BankUserGenerator(f'gen{i}')
        gen_list.append(gen)    
        ss.register_entity(gen)    
        
    que = BankQueue('Queue', queue_size, proc_num)
    ss.register_entity(que)
    
    account_list = []
    for i in range(proc_num) :
        account = BankAccountant('BankAccountant', i)
        account_list.append(account)
        ss.register_entity(account)
        
    result = BankResult('result', max_user)
    ss.register_entity(result)
        
    ## Model Relation
    ss.insert_input_port('start')

    for gen in gen_list : 
        ss.coupling_relation(None, 'start', gen, 'start')
        ss.coupling_relation(gen, 'user_out', que, 'user_in')
    ss.coupling_relation(que, "result", result, "drop")
    for i in range(proc_num) : 
        ss.coupling_relation(que, f'proc{i}', account_list[i], 'in')
        ss.coupling_relation(account_list[i], 'next', que, 'proc_checked')
        ss.coupling_relation(account_list[i], 'next', result, 'process')
        
    ss.insert_external_event('start', None)
    #print()
    ## simulation run  
    for i in range(max_simtime):
        #print("[time] : ", i)
        ss.simulate(1)
               
                

execute_simulation(1, ExecutionType.V_TIME)
    