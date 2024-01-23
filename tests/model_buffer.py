from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage


class Buffer(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Delay", 0)

        self.insert_input_port("recv")
        self.insert_output_port("output")
        self._msg = None

    def ext_trans(self, port, msg):
        if port == "recv":
            print(f"[Buf][IN]: recv")
            self._msg = msg
            self._cur_state = "Delay"

    def output(self):
        print(f"[Buf][OUT]: {self._msg.retrieve()[0]}")
        msg = SysMessage(self.get_name(), "output")
        #msg.insert(f"{self._msg[0].msg_no}")
        return msg

    def int_trans(self):
        if self._cur_state == "Delay":
            self._cur_state = "Wait"
