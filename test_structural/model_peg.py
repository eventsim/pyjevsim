from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage


class PEG(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Generate", 1)

        self.insert_input_port("start")
        self.insert_output_port("process1")
        self.insert_output_port("process2")
        self.insert_output_port("process3")

        self.msg_no = 0

    def ext_trans(self, port, msg):
        if port == "start":
            print(f"[{self.get_name()}][IN]: started")
            self._cur_state = "Generate"

    def output(self):
        if self.msg_no % 3 == 0 and self.msg_no != 0 :
            msg = SysMessage(self.get_name(), "process3")
        elif self.msg_no % 2 == 0 and self.msg_no != 0:
            msg = SysMessage(self.get_name(), "process2")
        else : 
            msg = SysMessage(self.get_name(), "process1")
        msg.insert(f"{self.msg_no}")
        print(f"[{self.get_name()}][OUT]: {self.msg_no}")
        return msg

    def int_trans(self):
        if self._cur_state == "Generate":
            self._cur_state = "Generate"
            self.msg_no += 1
