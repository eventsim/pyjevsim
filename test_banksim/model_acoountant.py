from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage

class BankAccountant(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)

        self.init_state("WAIT")
        self.insert_state("WAIT", Infinite)
        self.insert_state("PROC", 1)
        self.insert_state("EMPTY", 0)

        self.insert_input_port("check")
        self.insert_input_port("in")

        self.insert_output_port("next")

        self.user = None
        self.proc_user = []

    def ext_trans(self, port, msg):
        _time = self.global_time   
        if port == "check":
            if self._cur_state == "WAIT":
                print("[A] WAIT")
                self._cur_state = "EMPTY"
            else:
                self.cancel_rescheduling()

        if port == "in":
            self.user = msg.retrieve()[0]
            self._cur_state = "PROC"
            self.update_state("PROC", self.user.get_service_time())
            print(f"[A][arrive] ID:{self.user.get_id()} Time:{_time}")
        pass
            
    def output(self):
        _time = self.global_time   
        msg = None
        if self._cur_state == "PROC":
            cur_time = self.global_time   
            self.user.calc_wait_time(cur_time)
            self.proc_user.append(self.user)
            print(f"[A][processed] ID:{self.user.get_id()} Time:{_time}")

            msg = SysMessage(self.get_name(), "next")

        elif self._cur_state == "EMPTY":
            print("[A] EMPTY")
            msg = SysMessage(self.get_name(), "next")			

        return msg

    def int_trans(self):
        if self._cur_state == "PROC":
                self._cur_state = "WAIT"
        elif self._cur_state == "EMPTY":
            self._cur_state = "WAIT"

    def __del__(self):
        for user in self.proc_user:
            print(user)

    def __str__(self):
        return f">> {self.get_name()}, State:{self._cur_state}, {self.user}"
