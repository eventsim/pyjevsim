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

from .model_accountant import BankAccountant
from .model_queue import BankQueue
from .model_user_gen import BankUserGenerator

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    ss = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=None)
        
    gen_num = 10            #Number of BankUserGenerators 
    queue_size = 100        #BankQueue size
    proc_num = 30           #Number of BankAccountant
    
    user_process_time = 5   #BankUser's processing speed
    gen_cycle = 2           #BankUser Generattion cycle
    max_user = 500000       #Total number of users generated
    
    max_simtime = 150000    #simulation time
    wiq_time = 100000       #what-if-question poinst
        
        
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
        account = BankAccountant('BankAccountant', i)
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

    ## simulation run  
    for i in range(max_simtime):
        #print("[time] : ", i)
        ss.simulate(1)
        
        if i == wiq_time : # what if question point
            #Please check the journal or document for "test case"
            
            ##test case2 or 3
            ##wiq : parameter 
            #for gen in gen_list : 
            #    gen.set_cycle(1)
            #    gen.set_cycle(3)
            
            ##test case4 : Generator Model reduction           
            #for j in range(5, 10) :
            #    ss.remove_relation(f'gen{j}', 'user_out', 'Queue', 'user_in')
            #    ss.get_entity(gen_list[j])
            
            ## test case5 : Generator Model increase
            #new_gen_num = 15
            #user = gen_list[-1].get_user()
            #print("user test", user)
            #for j in range(gen_num, new_gen_num) :
            #    gen = BankUserGenerator(f'gen{j}', gen_cycle, user, user_process_time)
            #    gen_list.append(gen)    
            #    ss.register_entity(gen)
            #    ss.coupling_relation(None, 'start', gen, 'start')
            #    ss.coupling_relation(gen, 'user_out', que, 'user_in')
            #ss.insert_external_event('start', None)
            pass                

start_time = time.time()
execute_simulation(1, ExecutionType.V_TIME)
end_time = time.time()
execution_time = end_time - start_time
print(f"run time: {execution_time} sec")
    