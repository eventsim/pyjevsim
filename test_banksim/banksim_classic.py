""" """
from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor

from .model_acoountant import BankAccountant
from .model_queue import BankQueue
from .model_user_gen import BankUserGenerator

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    ss = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=None)
    
    gen_num = 3             #Number of BankUserGenerators 
    queue_size = 10         #BankQueue size
    proc_num = 5            #Number of BankAccountant
    
    user_process_time = 3   #BankUser's processing speed
    gen_cycle = 2           #BankUser Generattion cycle
    max_user = 50000        #Total number of users generated
    
    max_simtime = 100000    #simulation time
    
    
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
        ss.simulate(1)
    
def test_casual_order1(capsys):
    execute_simulation(1, ExecutionType.V_TIME)
    print(capsys)
    