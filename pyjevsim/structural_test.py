from system_executor import SysExecutor
from system_message import SysMessage
from definition import *
import datetime

from structural_model import StructuralModel
from behavior_model import BehaviorModel


class PEG(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Generate", 1)

        self.insert_input_port("start")
        self.insert_output_port("process")

        self.msg_no = 0

    def ext_trans(self,port, msg):
        if port == "start":
            print(f"[Gen][IN]: started")
            self._cur_state = "Generate"

    def output(self):
        msg = SysMessage(self.get_name(), "process")
        msg.insert(f"[Gen][OUT]: {self.msg_no}")
        print(f"[Gen][OUT]: {self.msg_no}")
        return msg
        
    def int_trans(self):
        if self._cur_state == "Generate":
            self._cur_state = "Generate"
            self.msg_no += 1

class MsgRecv (BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)

        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_input_port("recv")

    def ext_trans(self,port, msg):
        if port == "recv":
            print(f"[MsgRecv][IN]: {datetime.datetime.now()}")
            data = msg.retrieve()
            print(data[0])
            self._cur_state = "Wait"

    def output(self):
        return None
        
    def int_trans(self):
        if self._cur_state == "Wait":
            self._cur_state = "Wait"

class STM(StructuralModel):
    def __init__(self, name):
        StructuralModel.__init__(self, name)
        
        self.insert_input_port("start")
        peg = PEG("GEN")
        self.register_entity(peg)
        proc = MsgRecv("PROC")
        self.register_entity(proc)

        self.coupling_relation(self, "start", peg, "start")
        self.coupling_relation(peg, "process", proc, "recv")


# System Simulator Initialization
ss = SysExecutor(1, _sim_mode="REAL_TIME")
#ss.register_engine("first", "REAL_TIME", 1)
ss.insert_input_port("start")
#gen = PEG(0, Infinite, "Gen", "first")
#ss.register_entity(gen)

gen = STM("Gen")
ss.register_entity(gen, inst_t=3)

ss.coupling_relation(ss, "start", gen, "start")
ss.insert_external_event("start", None)
ss.simulate()