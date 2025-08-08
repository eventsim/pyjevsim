"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
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
import sys
import contexts
import yaml

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor
from pyjevsim.snapshot_manager import SnapshotManager

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

snapshot_manager = SnapshotManager()
ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=snapshot_manager)

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
    account = BankAccountant(f'processor{i}', i)
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

# simulation run

i = 0    
while(True) : 
    # Snapshot when simulation time is what-if-qustion point
    if i == wiq_time : 
        ss.snapshot_simulation(name = "banksim", directory_path = "./snapshot")
        #result.get_result()
        break        
    ss.simulate(1)
    i+= 1 