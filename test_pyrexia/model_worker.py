from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage


class WorkerManager(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)

        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Worker", 1)
        
        self.insert_input_port("worker_check")
        self.insert_output_port("process")

        self.human = None
        
    def ext_trans(self, port, msg):        
        if port == "worker_check" : 
            self._cur_state = "Worker"
            
            data = msg.retrieve()
            self.human = data[0]
            
            print(f"[WORK][IN]: {self.human}")
            

    def output(self):
        msg = SysMessage(self.get_name(), "process")
        msg.insert(self.human)
        print(f"[WORK][OUT]: {self.human}")
        return msg

    def int_trans(self):
        if self._cur_state == "Worker":
            self._cur_state = "Wait"
