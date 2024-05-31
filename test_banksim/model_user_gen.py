from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage
from pyjevsim.system_executor import SysExecutor

class BankUser:
    def __init__(self, _id:int, s_t:float):
        self.user_id 	= _id
        self.wait_t     = 0.0
        self.done_t 	= 0.0
        self.arrival_t 	= 0.0
        self.service_t 	= s_t

    def get_id(self) -> int :
        return self.user_id

    def get_wait_time(self) -> float:
        return self.wait_t

    def get_arrival_time(self) -> float:
        return self.arrival_t

    def get_service_time(self) -> float:
        return self.service_t

    def set_arrival_time(self, a_t:float) -> None:
        self.arrival_t = a_t

    def calc_wait_time(self, w_t:float) -> None:
        self.done_t = w_t
        self.wait_t = w_t - self.arrival_t

    def __str__(self):
        return f"{self.get_id()}, {self.service_t}, {self.arrival_t}, {self.done_t}, {self.wait_t}"

class BankUserGenerator(BehaviorModel):
    def __init__(self, name, cycle, max_user, proc_time):
        BehaviorModel.__init__(self, name)
        self.init_state("WAIT")
        self.insert_state("WAIT", Infinite)
        self.insert_state("GEN", cycle)

        self.insert_input_port("start")
        self.insert_output_port("user_out")

        self.cycle = cycle
        self.generated_user = 0
        self.max_user = max_user
        self.proc_time = proc_time
        
    def ext_trans(self, port, msg):
        if port == "start":
            print(f"[Gen][IN]: started")
            self._cur_state = "GEN"

    def output(self):
        _time = self.global_time        
        print(f"[G] ID:{self.get_name()}-{self.generated_user} Time:{_time}")

        msg = SysMessage(self.get_name(), "user_out")

        bu = BankUser(f"{self.get_name()}-{self.generated_user}", self.proc_time)
        bu.set_arrival_time(_time)
        msg.insert(bu)

        self.generated_user += 1
        return msg

    def int_trans(self):
        if self._cur_state == "GEN" and self.generated_user >= self.max_user: # 
            self._cur_state = "WAIT"
        else:
            self.update_state("GEN", self.cycle)
            
    def set_cycle(self, cycle) :
        self.cycle = cycle
