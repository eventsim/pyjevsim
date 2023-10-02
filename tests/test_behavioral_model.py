#!/usr/bin/env python

# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

import time
import math
from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor
from .model_peg import PEG
from .model_msg_recv import MsgRecv


def execute_simulation(execution_mode):
    # System Executor Initialization
    se = SysExecutor(1, ex_mode=execution_mode)
    se.insert_input_port("start")

    # Model Creation
    gen = PEG("Gen")
    proc = MsgRecv("Proc")

    # Register Model to Engine
    se.register_entity(gen)
    se.register_entity(proc)

    # Set up relation among models
    se.coupling_relation(se, "start", gen, "start")
    se.coupling_relation(gen, "process", proc, "recv")

    # Inject External Event to Engine
    se.insert_external_event("start", None)

    for _ in range(3):
        se.simulate(1)

# Test Suite
def test_casual_order1(capsys):
    execute_simulation(ExecutionType.V_TIME)
    captured = capsys.readouterr()
    desired_output = "[Gen][IN]: started\n[Gen][OUT]: 0\n"\
                     + "[MsgRecv][IN]: 0\n[Gen][OUT]: 1\n[MsgRecv][IN]: 1\n"
    assert captured.out == desired_output

def test_execution_mode():
    before = time.perf_counter()
    execute_simulation(ExecutionType.R_TIME)
    after = time.perf_counter()
    assert math.isclose((after - before), 3, rel_tol=0.01)
