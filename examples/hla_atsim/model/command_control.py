from pyjevsim import BehaviorModel, Infinite

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
            self.threat_list = msg.retrieve()[0]
            self._cur_state = "Decision"

    def output(self, msg_deliver):
        # Reference from the frozen snapshot (order-independent), like the
        # Detector. The heading change is staged as pending_heading and
        # committed at the next tick boundary (see utils/ticking.py) so it
        # cannot race the Manuever integration within this tick.
        snap = self.platform.ctx.snapshot
        me = snap.get(self.platform.sense_id)
        for target in self.threat_list:
            if me is not None and self.platform.co.threat_evaluation(me, target):
                # send order
                message = SysMessage(self.get_name(), "launch_order")
                msg_deliver.insert_message(message)
                # stage evasion heading (applied next tick)
                self.platform.mo.pending_heading = self.platform.co.get_evasion_heading()

        self.threat_list = []
        
    def int_trans(self):
        if self._cur_state == "Decision":
            self._cur_state = "Wait"