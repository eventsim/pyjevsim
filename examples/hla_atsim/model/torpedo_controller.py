import platform
from pyjevsim import BehaviorModel, Infinite
import datetime

from pyjevsim.system_message import SysMessage

class TorpedoCommandControl(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)
        
        self.platform = platform
        
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Decision", 0)

        self.insert_input_port("threat_list")
        self.insert_output_port("target")
        self.threat_list = []

    def ext_trans(self,port, msg):
        if port == "threat_list":
            print(f"{self.get_name()}[threat_list]: {datetime.datetime.now()}")
            self.threat_list = msg.retrieve()[0]
            self._cur_state = "Decision"

    def output(self, msg_deliver):
        # Reference from the frozen snapshot (order-independent). The pursuit
        # target is staged as pending_target and committed at the next tick
        # boundary (see utils/ticking.py), so TrackingManuever reads it
        # deterministically instead of via a live message that used
        # cancel_rescheduling (a source of intra-tick nondeterminism).
        snap = self.platform.ctx.snapshot
        me = snap.get(self.platform.sense_id)
        target = None

        if me is not None:
            for t in self.threat_list:
                target = self.platform.co.get_target(me, t)

        # house keeping
        self.threat_list = []
        self.platform.co.reset_target()

        if target:
            self.platform.mo.pending_target = target
        
    def int_trans(self):
        if self._cur_state == "Decision":
            self._cur_state = "Wait"