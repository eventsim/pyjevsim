#!/usr/bin/env python

# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor

from .model_msg_recv import MsgRecv
from .model_peg import PEG
from .model_stm import STM


def execute_simulation():
    # System Simulator Initialization
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    # se.register_engine("first", "REAL_TIME", 1)
    se.insert_input_port("start")
    # gen = PEG(0, Infinite, "Gen", "first")
    # se.register_entity(gen)

    gen = STM("Gen")
    se.register_entity(gen, inst_t=3)

    peg = PEG("GEN")
    se.register_entity(peg)

    se.coupling_relation(se, "start", gen, "start")
    se.coupling_relation(se, "start", peg, "start")

    se.insert_external_event("start", None)
    for _ in range(5):
        se.simulate(1)


def test_f(capsys):
    execute_simulation()
    captured = capsys.readouterr()
