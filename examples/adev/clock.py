from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *

import os
import datetime

from config import *
#from instance.config import *

import math

class Clock(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)
        self.init_state("IDLE")
        self.insert_state("IDLE", Infinite)
        self.insert_state("WAKE", 1)
  
        self.insert_input_port("start")
        self.insert_input_port("end")
        
        self.sim_time = 0

    def ext_trans(self,port, msg):
        if port == "start":
            self._cur_state = "WAKE"
        if port == "end":
            print("end")
            self._cur_state = "IDLE"
                        
    def output(self, msg_deliver):
        if self._cur_state == "WAKE":
            
            self.sim_time += 1
            #if self.sim_time%24==0:
            #    print('-'*40,self.convert_unit_time(),'-'*40)
            
            #return msg
            print("progress")

    def int_trans(self):
        if self._cur_state == "WAKE":
            self._cur_state = "WAKE"
    
    def convert_unit_time(self):
        return '{0} day {1} Hour'.format(math.trunc(self.sim_time / 24), self.sim_time % 24)