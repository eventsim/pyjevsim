from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage


class MsgRecv(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)

        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_input_port("recv")

    def ext_trans(self, port, msg):
        if port == "recv":
            data = msg.retrieve()
            print(f"[MsgRecv][IN]: {data[0]}")
            self._cur_state = "Wait"

    def output(self):
        return None

    def int_trans(self):
        if self._cur_state == "Wait":
            self._cur_state = "Wait"
