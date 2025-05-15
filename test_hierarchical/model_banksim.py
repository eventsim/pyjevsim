"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Structural Model
"""

import time

from pyjevsim.structural_model import StructuralModel


from pyjevsim.definition import *

from .model_accountant import BankAccountant
from .model_queue import BankQueue
from .model_user_gen import BankUserGenerator

class STM(StructuralModel):
    def __init__(self, name):
        StructuralModel.__init__(self, name)
        
        gen_num = 3            #Number of BankUserGenerators 
        queue_size = 10        #BankQueue size
        proc_num = 5         #Number of BankAccountant
        
        user_process_time = 1   #BankUser's processing speed
        gen_cycle = 2           #BankUser Generattion cycle
        max_user = 300       #Total number of users generated
        

        ## model set & register entity
        gen_list = []
        user = int(max_user / gen_num)
        for i in range(gen_num) :
            if i == gen_num-1:
                user += max_user % gen_num
            gen = BankUserGenerator(f'gen{i}', gen_cycle, user, user_process_time)
            gen_list.append(gen)    
            self.register_entity(gen)    
            
        que = BankQueue('Queue', queue_size, proc_num)
        self.register_entity(que)
        
        
        account_list = []
        for i in range(proc_num) :
            account = BankAccountant('BankAccountant', i)
            account_list.append(account)
            self.register_entity(account)
            
            
        self.insert_input_port("start")
        
        
        for gen in gen_list : 
            self.coupling_relation(self, 'start', gen, 'start')
            self.coupling_relation(gen, 'user_out', que, 'user_in')
        for i in range(proc_num) : 
            self.coupling_relation(que, f'proc{i}', account_list[i], 'in')
            self.coupling_relation(account_list[i], 'next', que, 'proc_checked')
            
        #print(self.port_map)