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
import sys
import contexts
import yaml

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor

from examples.banksim.model.model_accountant import BankAccountant
from examples.banksim.model.model_queue import BankQueue
from examples.banksim.model.model_user_gen import BankUserGenerator
from examples.banksim.model.model_result import BankResult

with open("scenario.yaml", "r") as f:
    config = yaml.safe_load(f)
    
gen_num, queue_size, proc_num, max_user, max_simtime = (
    config["gen_num"],
    config["queue_size"],
    config["proc_num"],
    config["max_user"],
    config["max_simtime"],
)
wiq_time = int(sys.argv[1])
wiq_gen_num = int(sys.argv[2])

ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)

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

## simulation run  
while(True):
    if wiq_gen_num < gen_num and i == wiq_time : 
        for _ in range(wiq_gen_num) :
            gen = gen_list.pop()
            gen.set_state_idle()
            
    if wiq_gen_num > gen_num and i == wiq_time : 
        for j in range(wiq_gen_num-gen_num) :
            gen = BankUserGenerator(f'gen{j}')
            gen_list.append(gen)    
            ss.register_entity(gen)    
            ss.coupling_relation(None, 'start', gen, 'start')
            ss.coupling_relation(gen, 'user_out', que, 'user_in')
            ss.insert_external_event('start', None)
    
    ss.simulate(1)
            