from system_executor import SysExecutor
from system_message import SysMessage
from definition import *
import datetime
from behavior_model import BehaviorModel
from behavior_model_executor import BehaviorModelExecutor

class PEG(BehaviorModel):
    def __init__(self, instance_time, destruct_time, name, engine_name):
        self.instance_time = instance_time
        self.destruct_time = destruct_time
        
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Generate", 1)

        self.insert_input_port("start")
        self.insert_output_port("process")

    def get_instance_time(self):
        return self.instance_time
    
    def get_destruct_time(self):
        return self.destruct_time
    
    
    def ext_trans(self,port, msg):
        if port == "start":
            print(f"[Gen][IN]: {datetime.datetime.now()}")
            self._cur_state = "Generate"

    def output(self):
        msg = SysMessage(self.get_name(), "process")
        msg.insert(f"[Gen][OUT]: {datetime.datetime.now()}")
        return msg
        
    def int_trans(self):
        if self._cur_state == "Generate":
            self._cur_state = "Generate"


# System Simulator Initialization
ss = SysExecutor(0.1)
#ss.register_engine("first", "REAL_TIME", 1)
ss.insert_input_port("start")
gen = PEG(0, Infinite, "Gen", "first")
ss.register_entity(gen)
ss.coupling_relation(None, "start", gen, "start")
#ss.coupling_relation(gen, "process", proc, "recv")
ss.insert_external_event("start", None)
ss.simulate()