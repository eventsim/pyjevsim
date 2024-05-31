#!/usr/bin/env python

# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

from pyjevsim.definition import *
from pyjevsim.definition import ExecutionType
from pyjevsim.system_executor import SysExecutor
from .model_stm import STM
from .model_msg_recv import MsgRecv

def test_f():
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    se.insert_input_port("start")

    gen = STM("Gen")
    mr1 = MsgRecv("MsgRecv1")
    mr2 = MsgRecv("MsgRecv2")
    mr3 = MsgRecv("MsgRecv3")
        
    se.register_entity(gen)
    se.register_entity(mr1)
    se.register_entity(mr2)
    se.register_entity(mr3)

    se.coupling_relation(se, "start", gen, "start")
    se.coupling_relation(gen, "output1", mr1, "recv")
    se.coupling_relation(gen, "output2", mr2, "recv")
    se.coupling_relation(gen, "output3", mr3, "recv")
    se.insert_external_event("start", None)

    se.simulate(20)
    #print(se.product_port_map)

    
    #assert mr.msg_recv > 0