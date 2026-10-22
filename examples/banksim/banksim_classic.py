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

After wiq_time simulate(1) steps the number of running generators changes
to wiq_gen_num (the what-if question); the run ends when max_user users
have been served.

Usage:
From examples/banksim, run

   python banksim_classic.py <wiq_time> <wiq_gen_num> [--seed N] [--max-user N]

Without --seed (and without a 'seed' key in scenario.yaml) the run is
unseeded, as before.
"""
import contexts

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor

from examples.banksim.model.model_accountant import BankAccountant
from examples.banksim.model.model_user_gen import BankUserGenerator
from examples.banksim.runner import parse_args, load_config, bank_classes, apply_what_if
from examples.banksim.seeding import model_rng

args = parse_args("Bank simulation, classic run with a what-if change at wiq_time.")
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

Queue, Result = bank_classes(seed)

ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)

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
    account = BankAccountant('BankAccountant', i)
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

## simulation run (BankResult ends the process once max_user users are served)
tick = 0
while(True):
    # What-if: after wiq_time steps, the same point at which
    # banksim_snapshot.py takes its snapshot.
    if tick == wiq_time :
        apply_what_if(ss, gen_num, wiq_gen_num, que, seed)
    ss.simulate(1)
    tick += 1
