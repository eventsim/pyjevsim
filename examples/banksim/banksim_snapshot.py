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

The simulation is saved to ./snapshot after wiq_time simulate(1) steps,
the point at which banksim_classic.py applies the what-if change;
banksim_restore.py continues it with the same change.  With --seed the
models are the same as in a seeded banksim_classic.py run and the snapshot
holds the same model states, but the restored run is not the same
simulation: see banksim_restore.py.

Usage:
From examples/banksim, run

   python banksim_snapshot.py <wiq_time> <wiq_gen_num> [--seed N] [--max-user N]

Without --seed (and without a 'seed' key in scenario.yaml) the run is
unseeded, as before.
"""
import contexts

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor
from pyjevsim.snapshot_manager import SnapshotManager

from examples.banksim.model.model_accountant import BankAccountant
from examples.banksim.model.model_user_gen import BankUserGenerator
from examples.banksim.runner import parse_args, load_config, bank_classes
from examples.banksim.seeding import model_rng

args = parse_args("Bank simulation: run wiq_time steps and snapshot the simulation.")
config = load_config(args)

gen_num, queue_size, proc_num, max_user, max_simtime, seed = (
    config["gen_num"],
    config["queue_size"],
    config["proc_num"],
    config["max_user"],
    config["max_simtime"],
    config["seed"],
)
wiq_time = args.wiq_time
wiq_gen_num = args.wiq_gen_num

snapshot_manager = SnapshotManager()
Queue, Result = bank_classes(seed)

ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=snapshot_manager)

## model set & register entity
gen_list = []
for i in range(gen_num) :
    gen = BankUserGenerator(f'gen{i}', rng=model_rng(seed, f'gen{i}'))
    gen_list.append(gen)
    ss.register_entity(gen)

que = Queue('Queue', queue_size, proc_num)
ss.register_entity(que)


account_list = []
for i in range(proc_num) :
    account = BankAccountant(f'processor{i}', i)
    account_list.append(account)
    ss.register_entity(account)

result = Result('result', max_user)
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

tick = 0
while(True) :
    # Snapshot when simulation time is what-if-qustion point
    if tick == wiq_time :
        ss.snapshot_simulation(name = "banksim", directory_path = "./snapshot")
        #result.get_result()
        break
    ss.simulate(1)
    tick += 1
