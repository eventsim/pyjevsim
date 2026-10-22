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

The restored simulation gets the what-if change (wiq_gen_num running
generators) and runs until max_user users have been served.  Use the same
arguments and --seed as for banksim_snapshot.py: the seed is needed for the
generators that the what-if change adds (the restored ones carry their
streams in the snapshot).  max_user comes from the snapshot.

A simulation snapshot holds the models and their couplings, not the
simulation clock or the models' scheduled event times.  The restored run
therefore starts at time 0 with every model rescheduled from its saved
state (the users in service at the snapshot are reported done at time 0),
so it differs from banksim_classic.py continued past wiq_time even
with the same seed.  With the same seed, repeated snapshot + restore runs
are identical.

Usage:
From examples/banksim, run

   python banksim_restore.py <wiq_time> <wiq_gen_num> [--seed N]
"""
import contexts

from pyjevsim.definition import *
from pyjevsim.snapshot_manager import SnapshotManager
from pyjevsim.restore_handler import RestoreHandler
from examples.banksim.runner import parse_args, load_config, apply_what_if

args = parse_args("Bank simulation: restore the snapshot and apply the what-if change.")
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

snapshot_manager = SnapshotManager(RestoreHandler(1, ex_mode=ExecutionType.V_TIME, name = "banksim", path = "./snapshot"))
ss = snapshot_manager.get_engine() #Restore a snapshot simulation

apply_what_if(ss, gen_num, wiq_gen_num, ss.get_model('Queue'), seed)

## simulation run (BankResult ends the process once max_user users are served)
while(True) :
    ss.simulate(1)
