#!/usr/bin/env python

# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor

from .model_stm import STM


def test_f():
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)
    se.insert_input_port("start")

    gen = STM("Gen")
    se.register_entity(gen, inst_t=3)

    se.coupling_relation(se, "start", gen, "start")
    se.insert_external_event("start", None)
    se.simulate(5)

    gen = se.get_entity("Gen")
