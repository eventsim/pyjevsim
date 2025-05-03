import datetime
import math

from pyjevsim import BehaviorModel, Infinite
from utils.object_db import ObjectDB

from .decoy import Decoy
from mobject.staationary_decoy_object import StationaryDecoyObject

class Launcher(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)
        
        self.platform = platform
        
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Launch", 0)

        self.insert_input_port("order")

        self.launch_flag = False

    def ext_trans(self,port, msg):
        if port == "order":
            print(f"{self.get_name()}[order_recv]: {datetime.datetime.now()}")
            self._cur_state = "Launch"

    def output(self, msg):
        if not self.launch_flag:
            se = ObjectDB().get_executor()

            for idx, decoy in enumerate(self.platform.lo.get_decoy_list()):
                destroy_t = math.ceil(self.platform.lo.get_time_of_flight(decoy) + decoy['lifespan'])
                sdo = StationaryDecoyObject(self.platform.get_position(), decoy)
                ObjectDB().decoys.append(sdo)
                decoy_model = Decoy(f"[Decoy][{idx}]", sdo)
                se.register_entity(decoy_model, 0, destroy_t)

        self.launch_flag = True

        #se.register_entity()
        return None
        
    def int_trans(self):
        if self._cur_state == "Launch":
            self._cur_state = "Wait"