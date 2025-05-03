from pyjevsim import BehaviorModel, Infinite
import datetime
from utils.object_db import ObjectDB

class Launcher(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)
        
        self.platform = platform
        
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Launch", 0)

        self.insert_input_port("order")

    def ext_trans(self,port, msg):
        if port == "order":
            print(f"{self.get_name()}[order_recv]: {datetime.datetime.now()}")
            self._cur_state = "Launch"

    def output(self, msg):
        se = ObjectDB().get_executor()
        return None
        
    def int_trans(self):
        if self._cur_state == "Launch":
            self._cur_state = "Wait"