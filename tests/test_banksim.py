"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Banksim tests using Behavior Models and Structural Model.

Usage:
From a terminal in the parent directory, run the following command.

   pytest -s ./tests/test_banksim.py
"""

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor

from .model_bank_accountant import BankAccountant
from .model_bank_queue import BankQueue
from .model_bank_user_gen import BankUserGenerator
from .model_banksim_stm import BanksimSTM


def test_banksim_behavioral():
    """Test banksim with behavioral models (flat coupling)."""
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)

    gen_num = 3
    queue_size = 10
    proc_num = 5
    user_process_time = 1
    gen_cycle = 2
    max_user = 30

    gen_list = []
    user = int(max_user / gen_num)
    for i in range(gen_num):
        if i == gen_num - 1:
            user += max_user % gen_num
        gen = BankUserGenerator(f'gen{i}', gen_cycle, user, user_process_time)
        gen_list.append(gen)
        se.register_entity(gen)

    que = BankQueue('Queue', queue_size, proc_num)
    se.register_entity(que)

    account_list = []
    for i in range(proc_num):
        account = BankAccountant('BankAccountant', i)
        account_list.append(account)
        se.register_entity(account)

    se.insert_input_port('start')

    for gen in gen_list:
        se.coupling_relation(None, 'start', gen, 'start')
        se.coupling_relation(gen, 'user_out', que, 'user_in')
    for i in range(proc_num):
        se.coupling_relation(que, f'proc{i}', account_list[i], 'in')
        se.coupling_relation(account_list[i], 'next', que, 'proc_checked')

    se.insert_external_event('start', None)

    for _ in range(100):
        se.simulate(1)

    # Verify all users were processed
    total_processed = sum(len(a.proc_user) for a in account_list)
    assert total_processed == max_user, f"Expected {max_user} processed, got {total_processed}"


def test_banksim_structural():
    """Test banksim with structural model (hierarchical coupling)."""
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)

    model = BanksimSTM("banksim", gen_num=3, queue_size=10, proc_num=5,
                       user_process_time=1, gen_cycle=2, max_user=30)

    se.insert_input_port('start')
    se.register_entity(model)
    se.coupling_relation(None, 'start', model, 'start')
    se.insert_external_event('start', None)

    for _ in range(100):
        se.simulate(1)
