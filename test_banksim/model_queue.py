from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage

class BankQueue(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)
        self.init_state("WAIT")
        self.insert_state("WAIT", Infinite)
        self.insert_state("CHECK", 0)
        self.insert_state("READY", Infinite)
        self.insert_state("SEND", 0)

        self.insert_input_port("in")
        self.insert_input_port("next")

        self.insert_output_port("ready")
        self.insert_output_port("out")

        self.insert_state("SEND_OK", 0)
        self.insert_state("SEND_OK_AFTER", 0)
        self.insert_input_port("check")
        self.insert_output_port("ok")

        self.user = None

    def ext_trans(self, port, msg):
        _time = self.global_time   
        if port == "in":
            if not self.user:
                self.user = msg.retrieve()[0]
                print(f"{self.get_name()}[in] ID:{self.user.get_id()} Time:{_time}")
            else:
                print(f"User Dropped: {msg.retrieve()[0]}")

            
            self._cur_state = "CHECK"
        elif port == "next":
            if self.user:
                print(f"{self.get_name()} Confirm Time:{_time}")
                self._cur_state = "SEND"
            else:
                self._cur_state = "SEND_OK"

        elif port == "check":
            print(f"Receive Ack {self.get_name()}")
            if self.user:
                self.cancel_rescheduling()
            else:
                self._cur_state = "SEND_OK"
 
    def output(self):
        msg = None
        _time = self.global_time   
        if self._cur_state == "CHECK":
            print(f"{self.get_name()} Check")
            msg = SysMessage(self.get_name(), "ready")
        elif self._cur_state == "SEND":
            print(f"{self.get_name()}[out] ID:{self.user.get_id()} Time:{_time}")
            
            msg = SysMessage(self.get_name(), "out")
            msg.insert(self.user)
            self.user = None

        elif self._cur_state == "SEND_OK":
            print(f"SEND_OK {self.get_name()}")
            msg = SysMessage(self.get_name(), "ok")

        elif self._cur_state == "SEND_OK_AFTER":
            print(f"SEND_OK {self.get_name()}")
            msg = SysMessage(self.get_name(), "ok")

        return msg

    def int_trans(self):
        if self._cur_state == "WAIT":
                self._cur_state = "CHECK"
        elif self._cur_state == "CHECK":
            self._cur_state = "READY"

        elif self._cur_state == "SEND":
            self._cur_state = "SEND_OK_AFTER"
        elif self._cur_state == "SEND_OK":
            print(f"WAIT {self.get_name()}")
            self._cur_state = "WAIT"
        elif self._cur_state == "SEND_OK_AFTER":
            self._cur_state = "WAIT"

    def __str__(self):
        return f">> {self.get_name()}, State:{self._cur_state}, {self.user}"