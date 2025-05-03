from pyjevsim import BehaviorModel, Infinite
import datetime

class FireControlSystem(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)
        
        self.platform = platform
        
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Decision", 0)

        self.insert_input_port("threat_lst")

    def ext_trans(self,port, msg):
        if port == "threat_lst":
            print(f"{self.get_name()}[start_recv]: {datetime.datetime.now()}")
            self._cur_state = "Decision"

    def output(self, msg):
        #self.platform.mo.calc_next_pos_with_heading(1)
        msg.insert_message("target")
        return msg
        
    def int_trans(self):
        if self._cur_state == "Decision":
            self._cur_state = "Wait"