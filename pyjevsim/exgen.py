relay_example = """from pyjevsim import BehaviorModel, SysExecutor, SysMessage, Infinite, ExecutionType
import datetime

class PEG(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Generate", 1)

        self.insert_input_port("start")
        self.insert_output_port("process")

    def ext_trans(self, port, msg):
        if port == "start":
            print(f"[Gen][IN]: {datetime.datetime.now()}")
            self._cur_state = "Generate"

    def output(self, msg_deliver):
        msg = SysMessage(self.get_name(), "process")
        msg.insert(f"[Gen][OUT]: {datetime.datetime.now()}")
        msg_deliver.insert_message(msg)

    def int_trans(self):
        if self._cur_state == "Generate":
            self._cur_state = "Generate"

class MsgRecv(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)

        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_input_port("recv")

    def ext_trans(self, port, msg):
        if port == "recv":
            print(f"[MsgRecv][IN]: {datetime.datetime.now()}")
            data = msg.retrieve()
            print(data[0])
            self._cur_state = "Wait"

    def output(self, msg_deliver):
        pass

    def int_trans(self):
        if self._cur_state == "Wait":
            self._cur_state = "Wait"

# System Executor Initialization
se = SysExecutor(1, ex_mode=ExecutionType.R_TIME)
se.insert_input_port("start")
gen = PEG("Gen")
se.register_entity(gen)
proc = MsgRecv("Proc")
se.register_entity(proc)
se.coupling_relation(None, "start", gen, "start")
se.coupling_relation(gen, "process", proc, "recv")
se.insert_external_event("start", None)
se.simulate(5)
"""

periodic_example = """from pyjevsim import BehaviorModel, SysExecutor, Infinite, ExecutionType
import datetime

class PEx(BehaviorModel):
    def __init__(self, name):
        BehaviorModel.__init__(self, name)
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Generate", 1)

        self.insert_input_port("start")

    def ext_trans(self, port, msg):
        if port == "start":
            print(f"[Gen][IN]: {datetime.datetime.now()}")
            self._cur_state = "Generate"

    def output(self, msg_deliver):
        print(f"[Gen][OUT]: {datetime.datetime.now()}")

    def int_trans(self):
        if self._cur_state == "Generate":
            self._cur_state = "Generate"


se = SysExecutor(1, ex_mode=ExecutionType.R_TIME)
se.insert_input_port("start")
gen = PEx("Gen")
se.register_entity(gen)
se.coupling_relation(None, "start", gen, "start")
se.insert_external_event("start", None)
se.simulate(5)
"""

usage = """
Usage: python -m pyjevsim.exgen [example]

types of example:
   periodic:\t Prints event log periodically
   relay: \t A model sends an output event and another model receives the event
"""
import sys
if len(sys.argv) != 2:
    print(usage)
elif sys.argv[1] == "relay":
    with open("example_relay.py", "w") as f:
        f.write(relay_example)
    print("Generated: example_relay.py")
elif sys.argv[1] == "periodic":
    with open("example_periodic.py", "w") as f:
        f.write(periodic_example)
    print("Generated: example_periodic.py")
else:
    print(usage)
