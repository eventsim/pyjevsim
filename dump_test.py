from pyjevsim.system_message import SysMessage
from pyjevsim.definition import *
from pyjevsim.behavior_model import BehaviorModel
from dill import loads 

SYSTEM_VERSION = ["1.0"]

class PEG(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Generate", 1)

        self.insert_input_port("start")
        self.insert_output_port("process")

        self.msg_no = 0

    def ext_trans(self,port, msg):
        if port == "start":
            print(f"[Gen][IN]: started")
            self._cur_state = "Generate"

    def output(self):
        msg = SysMessage(self.get_name(), "process")
        msg.insert(f"[Gen][OUT]: {self.msg_no}")
        print(f"[Gen][OUT]: {self.msg_no}")
        return msg
        
    def int_trans(self):
        if self._cur_state == "Generate":
            self._cur_state = "Generate"
            self.msg_no += 1

def model_load(shotmodel, name = None) :
    model_info = loads(shotmodel)
    
    if model_info["version"] not in SYSTEM_VERSION :
        raise Exception(f"{model_info['model_name']} model type does not match pyjevsim version")
    
    model = model_info["model_data"]
    
    if  not isinstance(model, BehaviorModel) :
        raise Exception(f"{model_info['model_name']} is not of BehaviorModel type")
        
    if name != None : 
        model.set_name(name)
    
    return model

    
model = PEG("testname")
dump_data = model.model_snapshot()

print(model_load(dump_data))