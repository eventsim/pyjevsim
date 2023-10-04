#!/usr/bin/env python

# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

from pyjevsim.definition import *
from pyjevsim.definition import ExecutionType
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_executor import SysExecutor
from .model_stm import STM

class SnapshotExecutor(SysExecutor) :
    def __init__(self, _time_resolution, _sim_name="default", ex_mode=ExecutionType.V_TIME):
        super().__init__(_time_resolution, _sim_name, ex_mode)
    
    def snapshot_manger(self, shotmodel=None):
        if self.global_time >= 3 :
            print(self.get_entity("Gen"))
            


def test_f():
    se = SnapshotExecutor(1, ex_mode=ExecutionType.V_TIME)
    se.insert_input_port("start")

    gen = STM("Gen")
    se.register_entity(gen, inst_t=3)

    se.coupling_relation(se, "start", gen, "start")
    se.insert_external_event("start", None)
    se.simulate(5)

    gen = se.get_entity("Gen")

