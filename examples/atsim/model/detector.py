import project_config
from pyjevsim import BehaviorModel, Infinite
from utils.object_db import ObjectDB
import datetime

from pyjevsim.system_message import SysMessage

class Detector(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)
        
        self.platform = platform
        
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Detect", 1)

        self.insert_input_port("start")
        self.insert_output_port("threat_list")

    def ext_trans(self,port, msg):
        if port == "start":
            print(f"{self.get_name()}[start_recv]: {datetime.datetime.now()}")
            #print(ObjectDB().items)
            self._cur_state = "Detect"

    def output(self, msg):
        message = SysMessage(self.get_name(),  "threat_list")
        message.insert([])
        
        for target in ObjectDB().items:
            if self.platform.mo != target and target.check_active():
                if self.platform.do.detect(self.platform.mo, target):
                    message.retrieve()[0].append(target)
        if message.retrieve()[0]:
            msg.insert_message(message)
        return msg
        
    def int_trans(self):
        if self._cur_state == "Detect":
            self._cur_state = "Detect"