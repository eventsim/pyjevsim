#!/usr/bin/env python

# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage
from pyjevsim.definition import *
from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.structural_model import StructuralModel

class PEG(BehaviorModel):
    def __init__(self, name):
        super(PEG, self).__init__()
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Generate", 1)

        self.insert_input_port("start")
        self.insert_output_port("process")

        self.data = 0
    
    def ext_trans(self,port, msg):
        if port == "start":
            print(f"[Gen][IN]:start")
            self._cur_state = "Generate"

    def output(self):
        msg = SysMessage(self.get_name(), "process")
        msg.insert(f"[Gen][OUT]: {self.data}")
        return msg
        
    def int_trans(self):
        if self._cur_state == "Generate":
            self._cur_state = "Generate"
            self.data += 1


class MsgRecv (BehaviorModel):
    def __init__(self, name):
        super(MsgRecv, self).__init__()

        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_input_port("recv")

    def ext_trans(self,port, msg):
        if port == "recv":
            data = msg.retrieve()
            print(f"[MsgRecv][IN]: {data[0]}")
            self._cur_state = "Wait"

    def output(self):
        return None
        
    def int_trans(self):
        if self._cur_state == "Wait":
            self._cur_state = "Wait"


def execute_simulation():
    # System Executor Initialization
    se = SysExecutor(1, _sim_mode="VIRTUAL_TIME")
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
def test_f(capsys):
    execute_simulation()
    captured = capsys.readouterr()
    desired_output = "[Gen][IN]:start\n[MsgRecv][IN]: [Gen][OUT]: 0\n[MsgRecv][IN]: [Gen][OUT]: 1\n"
    assert captured.out == desired_output