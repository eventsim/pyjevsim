"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Banksim Structural Model
"""

from pyjevsim.structural_model import StructuralModel
from pyjevsim.definition import *

from .model_bank_accountant import BankAccountant
from .model_bank_queue import BankQueue
from .model_bank_user_gen import BankUserGenerator


class BanksimSTM(StructuralModel):
    def __init__(self, name, gen_num=3, queue_size=10, proc_num=5,
                 user_process_time=1, gen_cycle=2, max_user=300):
        StructuralModel.__init__(self, name)

        gen_list = []
        user = int(max_user / gen_num)
        for i in range(gen_num):
            if i == gen_num - 1:
                user += max_user % gen_num
            gen = BankUserGenerator(f'gen{i}', gen_cycle, user, user_process_time)
            gen_list.append(gen)
            self.register_entity(gen)

        que = BankQueue('Queue', queue_size, proc_num)
        self.register_entity(que)

        account_list = []
        for i in range(proc_num):
            account = BankAccountant('BankAccountant', i)
            account_list.append(account)
            self.register_entity(account)

        self.insert_input_port("start")

        for gen in gen_list:
            self.coupling_relation(self, 'start', gen, 'start')
            self.coupling_relation(gen, 'user_out', que, 'user_in')
        for i in range(proc_num):
            self.coupling_relation(que, f'proc{i}', account_list[i], 'in')
            self.coupling_relation(account_list[i], 'next', que, 'proc_checked')
