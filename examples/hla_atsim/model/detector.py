import project_config
from pyjevsim import BehaviorModel, Infinite
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

    def ext_trans(self, port, msg):
        if port == "start":
            print(f"{self.get_name()}[start_recv]: {datetime.datetime.now()}")
            self._cur_state = "Detect"

    def output(self, msg_deliver):
        message = SysMessage(self.get_name(), "threat_list")
        message.insert([])

        # Read the frozen end-of-previous-tick snapshot, never live objects.
        snap = self.platform.ctx.snapshot
        me = snap.get(self.platform.sense_id)
        if me is None:
            return

        for target in snap.entries():                 # sorted by sense_id
            if target.sense_id == self.platform.sense_id:
                continue
            if target.check_active() and self.platform.do.detect(me, target):
                message.retrieve()[0].append(target)  # FrozenProxy (has get_position)

        if message.retrieve()[0]:
            msg_deliver.insert_message(message)

    def int_trans(self):
        if self._cur_state == "Detect":
            self._cur_state = "Detect"
