from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage


class ENVModel(BehaviorModel):
    def __init__(self, name, env_data):
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Environment", 0)

        self.insert_input_port("process")
        self.insert_output_port("work")
        self.insert_output_port("rest")

        self.env_data = env_data
        self.human = None
        
    def ext_trans(self, port, msg):
        if port == "process":
            self._cur_state = "Environment"
            data = msg.retrieve()
            self.human = data[0]
            
            
            self.human["health_score"] -= 0.1
            self.human["health_score"] = round(self.human["health_score"], 1)
            
            print("[ENV][IN]:", self.human["human_id"], ":", self.human["health_score"])
            

    def output(self):
        ##human info 계산
        if self.human["health_score"] > 5 :
            msg = SysMessage(self.get_name(), "work")
        else : 
            msg = SysMessage(self.get_name(), "rest")
        msg.insert(self.human)
        
        print("[ENV][OUT]:", self.human["human_id"], ":", self.human["health_score"])
        return msg

    def int_trans(self):
        if self._cur_state == "Environment":
            self._cur_state = "Wait"
