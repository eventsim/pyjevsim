import platform
from pyjevsim import BehaviorModel, Infinite
import datetime

from pyjevsim.system_message import SysMessage

class CommandControl(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)
        
        self.platform = platform
        
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Decision", 0)

        self.insert_input_port("threat_list")
        self.insert_output_port("launch_order")


        self.threat_list = []

    def ext_trans(self,port, msg):
        if port == "threat_list":
            print(f"{self.get_name()}[threat_list]: {datetime.datetime.now()}")
            self.threat_list = msg.retrieve()[0]
            self._cur_state = "Decision"

    def output(self, msg):
        for target in self.threat_list:
            if self.platform.co.threat_evaluation(self.platform.mo, target):
                # send order
                message = SysMessage(self.get_name(), "launch_order")
                msg.insert_message(message)
                # change heading
                self.platform.mo.change_heading(self.platform.co.get_evasion_heading())
        
        self.threat_list = []
        return msg
        
    def int_trans(self):
        if self._cur_state == "Decision":
            self._cur_state = "Wait"