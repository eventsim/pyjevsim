import project_config
from pyjevsim import BehaviorModel, Infinite
from object_db import ObjectDB
import datetime

class Detector(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)
        
        self.platform = platform
        
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Detect", 1)

        self.insert_input_port("start")

    def ext_trans(self,port, msg):
        if port == "start":
            print(f"{self.get_name()}[start_recv]: {datetime.datetime.now()}")
            print(ObjectDB().items)
            self._cur_state = "Detect"

    def output(self, msg):
        print(ObjectDB().items)
        for target in ObjectDB().items:
            if self.platform.mo != target:
                if self.platform.do.detect(self.platform.mo, target):
                    print(f"[Detected]({target.x}, {target.y}, {target.z})")

        return None
        
    def int_trans(self):
        if self._cur_state == "Detect":
            self._cur_state = "Detect"