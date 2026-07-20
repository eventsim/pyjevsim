from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.system_message import SysMessage
from pyjevsim.definition import *


from config import *



import copy

class Family(BehaviorModel):
    def __init__(self, name, family_type):
        BehaviorModel.__init__(self, name)
        
        self.init_state("IDLE")
        self.insert_state("IDLE", Infinite)
        self.insert_state("FLUSH", 0)

        self.insert_input_port("receive_membertrash") #trash input port from human
        self.insert_output_port("takeout_trash")  #trash output port -> garbage can

        self.family_type = family_type
        
    def ext_trans(self,port, msg):
        if port=="receive_membertrash":  #가족으로부터 쓰레기 받아서 누적, 쌓일경우 FLUSH상태로 변환
            data = msg.retrieve()
            
            self.family_type.get_members()[data[0]] += data[0].get_trash()
            self.family_type.stack_garbage(data[0].get_trash())
            
            if self.family_type.should_empty():
                if self.family_type.is_flush(data[0]):
                    self._cur_state = "FLUSH"

    def output(self, msg_deliver):
        msg = SysMessage(self.get_name(), "takeout_trash")
        msg.insert(copy.deepcopy(self.family_type.get_members()))
        self.family_type.empty_stack()

        msg_deliver.insert_message(msg)
            
    def int_trans(self):
        if self._cur_state == "FLUSH":
            self._cur_state = "IDLE"