"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Example of restoring Simulation snapshot to configure a bank simulation.

First, run banksim_snapshot.py before proceeding.

The User Generator Model generates a Bank User periodically.
The Bank Accountatnt handles the Bank User's operations,
Bank Queue stores the Bank User's data and passes the Bank User's information to the Bank Accountant when no Bank Accountant is available. 

Usage:
In a terminal in the parent directory, run the following command.

   pytest -s ./test_banksim/banksim_restore.py 
"""
import sys
import contexts
import yaml

from pyjevsim.definition import *
from pyjevsim.snapshot_manager import SnapshotManager
from pyjevsim.restore_handler import RestoreHandler
from examples.banksim.model.model_user_gen import BankUserGenerator

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

snapshot_manager = SnapshotManager(RestoreHandler(1, ex_mode=ExecutionType.V_TIME, name = "banksim", path = "./snapshot"))  
ss = snapshot_manager.get_engine() #Restore a snapshot simulation
        
if wiq_gen_num > gen_num :
    que = ss.get_model('Queue')
    for i in range(gen_num, wiq_gen_num) :
        gen = BankUserGenerator(f'gen{i}')
        ss.register_entity(gen)    
        ss.coupling_relation(None, 'start', gen, 'start')
        ss.coupling_relation(gen, 'user_out', que, 'user_in')
        ss.insert_input_port('start')
        ss.insert_external_event('start', None)

if wiq_gen_num < gen_num :
    for i in range(wiq_gen_num) :
        gen = ss.get_model(f'gen{i}')
        #ss.remove_entity(gen)
        gen.set_state_idle()

## simulation run
for i in range(max_simtime):
    ss.simulate(1)