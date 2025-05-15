from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.system_message import SysMessage
from pyjevsim.definition import *

import os
import datetime

from config import *
#from instance.config import *

from .job import TimeStruct
from .job import HumanType

class Human(BehaviorModel):
    def __init__(self, name, human):
        BehaviorModel.__init__(self, name)
        self.human= human
        self.init_state("IDLE")
        
        self.insert_state("IDLE", Infinite)
##
        unit_t = self.human.get_out().get_unit_time()
        print(self.human.get_type(), " out time:", unit_t)
        self.insert_state("WAIT", unit_t)
        #self.insert_state("WAIT", 1)
  
        self.insert_input_port("start")
        self.insert_input_port("end")
        
        self.insert_output_port("trash")  #쓰레기 배출포트?

    def ext_trans(self,port, msg):
        if port == "start":
            self._cur_state = "WAIT"
        if port == "end":
            self._cur_state = "IDLE"
                        
    def output(self, msg_deliver):
        if self._cur_state == "WAIT":
            #print("[human] " + self.get_name())
            msg = SysMessage(self.get_name(), "trash")
            msg.insert(self.human)
            
            #print("start?")
            return msg

    def int_trans(self):
        #print(self._cur_state)
        if self._cur_state == "WAIT":
            self._cur_state = "WAIT"
            unit_t = self.human.get_out().get_unit_time()
            #print(self.human.get_type(), " out time:", unit_t)
            self.update_state("WAIT", unit_t)
            #self.update_state("WAIT", 1)
