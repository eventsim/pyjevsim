from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage


class WorkModel(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)

        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Work", 1)
        
        self.insert_input_port("work")
        self.insert_output_port("process")
        self.insert_output_port("rest")

        self.human = None
        
    def ext_trans(self, port, msg):        
        if port == "work" : 
            self._cur_state = "Work"
            
            data = msg.retrieve()
            self.human = data[0]
            
            self.human["work_point"] += self.human["work_speed"]
            self.human["health_score"] -= self.human["work_speed"]
            self.human["health_score"] = round(self.human["health_score"], 1)
            
            print("[Work]")
            #print("[WORK][IN]:", self.human["human_id"], ":", self.human["health_score"])
            

    def output(self):
        if self.human["health_score"] > 5 :
            msg = SysMessage(self.get_name(), "process")
        else : 
            msg = SysMessage(self.get_name(), "rest")
        msg.insert(self.human)
        #print("[WORK][OUT]:", self.human["human_id"], ":", self.human["health_score"])
        print("[Work Point] : ", self.human["work_point"])
        return msg

    def int_trans(self):
        if self._cur_state == "Work":
            self._cur_state = "Wait"
