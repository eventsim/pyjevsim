from pyjevsim import BehaviorModel, Infinite
import datetime

class Decoy(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)
        
        self.platform = platform
        
        self.init_state("Maneuver")
        self.insert_state("Maneuver", 1)

    def ext_trans(self,port, msg):
        pass

    def output(self, msg):
        self.platform.calc_next_pos(1)
        return None
        
    def int_trans(self):
        if self._cur_state == "Maneuver":
            self._cur_state = "Maneuver"