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

    ## Requirements
    # - User는 ID로 구분된다. 
    # - User의 대기시간은 은행에 도착한 순간부터 기록한다. 
    # - 사용자의 서비스 시간은 랜덤하게 결정된다. 
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
    def __init__(self, name):
        BehaviorModel.__init__(self, name)
        self.init_state("WAIT")
        self.insert_state("WAIT", Infinite)
        self.insert_state("GEN", 1)

        self.insert_input_port("start")
        self.insert_output_port("user_out")

        self.generated_user = 0
        
    def ext_trans(self, port, msg):
        if port == "start":
            print(f"[Gen][IN]: started")
            self._cur_state = "GEN"

    def output(self):
        _time = self.global_time        
        print(f"[G] ID:{self.generated_user} Time:{_time}")

        msg = SysMessage(self.get_name(), "user_out")

        bu = BankUser(self.generated_user, 2)
        bu.set_arrival_time(_time)
        msg.insert(bu)

        self.generated_user += 1
        
        return msg

    def int_trans(self):
        if self._cur_state == "GEN" and self.generated_user >= 200: # 
            self._cur_state = "WAIT"
        else:
            self.update_state("GEN", 1)
