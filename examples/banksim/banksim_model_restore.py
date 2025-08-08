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
import sys
import contexts
import yaml
import time 
from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor
from pyjevsim.snapshot_manager import SnapshotManager
from pyjevsim.restore_handler import RestoreHandler

from examples.banksim.model.model_accountant import BankAccountant
from examples.banksim.model.model_queue import BankQueue

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

snapshot_manager = SnapshotManager(restore_handler=RestoreHandler()) 
ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)

## model restore & set register entity
#BankUserGenerator Restore

gen_list = []
for i in range(wiq_gen_num) :
    #BankUserGenerator Restore
    if i >= gen_num :
        with open(f"./snapshot/[time]gen0.simx", "rb") as f :
            gen = snapshot_manager.load_snapshot(f"gen{i}", f.read()) #restore model
    else : 
        with open(f"./snapshot/[time]gen{i}.simx", "rb") as f :
            gen = snapshot_manager.load_snapshot(f"gen{i}", f.read()) #restore model
    gen_list.append(gen)
    ss.register_entity(gen)  
    

with open(f"./snapshot/[time]result.simx", "rb") as f :
    result = snapshot_manager.load_snapshot(f"result", f.read()) #restore model   

with open(f"./snapshot/[time]Queue.simx", "rb") as f :
    que = snapshot_manager.load_snapshot(f"Queue", f.read()) #restore model   
que.que_reset(proc_num)
    
ss.register_entity(que)

ss.register_entity(result)
account_list = []
for i in range(proc_num) :
    account = BankAccountant(f'processor{i}', i)
    account_list.append(account)
    ss.register_entity(account)
    
ss.insert_input_port('start')
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
while(True):
    ss.simulate(1)
