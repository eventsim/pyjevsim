from pyjevsim import BehaviorModel, Infinite

class TrackingManuever(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)
        
        self.platform = platform
        
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Manuever", 1)

        self.insert_input_port("start")
        self.insert_input_port("target")

        self.target_platform = None
        self.idx = 0

    def ext_trans(self,port, msg):
        if port == "start":
            self._cur_state = "Manuever"
        elif port == "target":
            self.target_platform = msg.retrieve()[0]
            self.cancel_rescheduling()

    def output(self, msg_deliver):
        self.idx += 1
        if self.target_platform:
            if self.platform.mo.calc_next_pos_with_pos(self.target_platform, 1) < 5:
                self.target_platform = None
        else:
            self.platform.mo.calc_next_pos_with_heading(1)
        
    def int_trans(self):
        if self._cur_state == "Manuever":
            self._cur_state = "Manuever"