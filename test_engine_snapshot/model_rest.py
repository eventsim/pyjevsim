from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage


class RestModel(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)

        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Rest", 1)
        
        self.insert_input_port("rest")
        self.insert_output_port("process")
        
        self.insert_output_port("keep_rest")

        self.human = None
        
    def ext_trans(self, port, msg):        
        if port == "rest" : 
            self._cur_state = "Rest"
            
            data = msg.retrieve()
            self.human = data[0]
            
            self.human["health_score"] += 3
            self.human["health_score"] = round(self.human["health_score"], 1)
            print("[Rest]")
           #print("[REST][IN]:", self.human["human_id"], ":", self.human["health_score"])
            

    def output(self):
        if self.human["health_score"] > 5 :
            msg = SysMessage(self.get_name(), "process")
        else : 
            msg = SysMessage(self.get_name(), "keep_rest")
        msg.insert(self.human)
        #print("[REST][OUT]:", self.human["human_id"], ":", self.human["health_score"])
        return msg

    def int_trans(self):
        if self._cur_state == "Rest":
            self._cur_state = "Wait"
