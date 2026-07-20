from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *


from config import *

class Government(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)

        self.init_state("IDLE")
        self.insert_state("IDLE", Infinite)
        self.insert_state("PROCESS", 0)

        self.insert_input_port("recv_report")  #민원 발생시 받는 포트
        self.reported = {}

    def ext_trans(self,port, msg):
        if port == "recv_report":
            member=msg.retrieve()[0]
            if member.get_type() in self.reported:
                self.reported[member.get_type()] += 1
            else:
                self.reported[member.get_type()] = 1

    def __del__(self):
        output_str = ""
        for k, v in self.reported.items():
            output_str += f"{k},{v},"

    def output(self, msg_deliver):
        self.report += 1
            
        return None

    def int_trans(self):
        if self._cur_state == "PROCESS":
            self._cur_state = "IDLE"