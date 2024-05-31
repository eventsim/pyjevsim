from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *
from pyjevsim.system_message import SysMessage

class BankQueue(BehaviorModel):
    def __init__(self, name, queue_size, proc_num):
        BehaviorModel.__init__(self, name)
        self.init_state("WAIT")
        self.insert_state("WAIT", Infinite)
        self.insert_state("SEND", 0)
        
        self.insert_input_port("user_in")
        self.insert_input_port("proc_checked")

        self.usable_proc = []
        for i in range(proc_num) :
            self.insert_output_port(f"proc{i}")  
            self.usable_proc.append(f"proc{i}")
            
        self.proc_num = proc_num
        self.queue_size = queue_size
        self.user = []
        
    def set_queue_size(self, queue_size) : 
        self.queue_size = queue_size
    
    def ext_trans(self, port, msg):
        _time = self.global_time   
        if port == "user_in":
            if len(self.user) < self.queue_size:
                user = msg.retrieve()[0]
                self.user.append(user)
                print(f"{self.get_name()}[in] ID:{user.get_id()} Time:{_time}")
            else:
                print(f"User Dropped: {msg.retrieve()[0]}")
           
            self._cur_state = "SEND"
        elif port == "proc_checked":
            self.usable_proc.append(msg.retrieve()[0])
            self._cur_state = "SEND"
        
        if self.usable_proc == [] or self.user == [] :
            self._cur_state = "WAIT"    
             
    def output(self):
        msg = None
        _time = self.global_time
        if self._cur_state == "SEND":
            user = self.user.pop(0)
            print(f"{self.get_name()}[out] ID:{user.get_id()} Time:{_time}")
            
            msg = SysMessage(self.get_name(), self.usable_proc.pop(0))
            msg.insert(user)

        return msg

    def int_trans(self):
        if self._cur_state == "SEND":
            self._cur_state = "SEND"
        if self.usable_proc == [] or self.user == [] :
            self._cur_state = "WAIT"  
            
    def set_proc_num(self, proc_num) :
        if proc_num > self.proc_num : 
            for i in range(self.proc_num, proc_num) :
                self.insert_output_port(f"proc{i}")  
                self.usable_proc.append(f"proc{i}")
        elif proc_num < self.proc_num : 
            for i in range(proc_num, self.proc_num) :
                self.usable_proc.remove(f"proc{i}")
        
        self.proc_num = proc_num
        while len(self.user) > self.queue_size :
            print(f"User Dropped: {self.user.pop()}")
        
    def __str__(self):
        return f">> {self.get_name()}, State:{self._cur_state}, {self.user}"