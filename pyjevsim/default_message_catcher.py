from behavior_model_executor import BehaviorModelExecutor
#from behavior_model import BehaviorModel
from core_model import CoreModel
from system_message import SysMessage
from definition import *

class DefaultMessageCatcher(CoreModel, BehaviorModelExecutor):
    def __init__(self, instance_time, destruct_time, name, engine_name):
        CoreModel.__init__(self, name)
        BehaviorModelExecutor.__init__(self, instance_time, destruct_time, engine_name)
        self.instance_time = instance_time
        self.destruct_time = destruct_time
        #self.init_state("IDLE")
        #self.insert_state("IDLE", Infinite)

        self.insert_input_port("uncaught")
    
    def get_instance_time(self):
        return self.instance_time
    
    def get_destruct_time(self):
        return self.destruct_time
    
    def ext_trans(self, port, msg):
        data = msg.retrieve()

    def time_advance(self):
        return Infinite
