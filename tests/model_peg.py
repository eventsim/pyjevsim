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
        self.insert_output_port("process")

        self.msg_no = 0

    def ext_trans(self, port, msg):
        if port == "start":
            print(f"[Gen][IN]: started")
            self._cur_state = "Generate"

    def output(self):
        msg = SysMessage(self.get_name(), "process")
        msg.insert(f"{self.msg_no}")
        print(f"[Gen][OUT]: {self.msg_no}")
        return msg

    def int_trans(self):
        if self._cur_state == "Generate":
            self._cur_state = "Generate"
            self.msg_no += 1
