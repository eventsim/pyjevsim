from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage


class ENV(BehaviorModel):
    def __init__(self, name, env_data):
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Environment", 0)

        self.insert_input_port("env_check")
        self.insert_output_port("human_check")

        self.env_data = env_data
        self.human = None
        
    def ext_trans(self, port, msg):
        if port == "env_check":
            self._cur_state = "Environment"
            data = msg.retrieve()
            self.human = data[0]
            print(f"[ENV][IN]: {self.human}")
            

    def output(self):
        ##human info 계산
        msg = SysMessage(self.get_name(), "human_check")
        msg.insert(self.human)
        print(f"[ENV][OUT]: {self.human}")
        return msg

    def int_trans(self):
        if self._cur_state == "Environment":
            self._cur_state = "Wait"
