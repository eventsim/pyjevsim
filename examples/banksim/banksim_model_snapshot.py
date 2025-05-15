"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Example of snapshot a BankGenerator model during a Bank Simulation run.

The User Generator Model generates a Bank User periodically.
The Bank Accountatnt handles the Bank User's operations,
Bank Queue stores the Bank User's data and passes the Bank User's information to the Bank Accountant when no Bank Accountant is available. 

Usage:
In a terminal in the parent directory, run the following command.

   pytest -s ./test_banksim/banksim_model_snapshot.py 
"""
import sys
import contexts
import yaml

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor
from pyjevsim.snapshot_condition import SnapshotCondition
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

class BankGenModelCondition(SnapshotCondition) :
    @staticmethod
    def create_executor(behavior_executor) :
        return BankGenModelCondition(behavior_executor) #
    
    def __init__(self, behavior_executor):
        super().__init__(behavior_executor) #set behavior_executor
        self.check = True
        
    def snapshot_time_condition(self, global_time):
        if global_time >= wiq_time and self.check: #Snapshot at simulation time 10000
            self.check = False
            return True

snapshot_manager = SnapshotManager()
ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=snapshot_manager)

max_simtime = wiq_time+10    #simulation time
        
## model set & register entity
gen_list = []
for i in range(gen_num) :
    gen = BankUserGenerator(f'gen{i}')
    gen_list.append(gen)    
    ss.register_entity(gen)    
    
    #Associating snapshot conditions with models 
    snapshot_manager.register_snapshot_condition(f"gen{i}", BankGenModelCondition.create_executor)
    ss.register_entity(gen)        
    
que = BankQueue('Queue', queue_size, proc_num)
ss.register_entity(que)

account_list = []
for i in range(proc_num) :
    account = BankAccountant(f'processor{i}', i)
    account_list.append(account)
    ss.register_entity(account)
    
result = BankResult('result', max_user)
snapshot_manager.register_snapshot_condition(f"result", BankGenModelCondition.create_executor)

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
for i in range(max_simtime):
    ss.simulate(1)