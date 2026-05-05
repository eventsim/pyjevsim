"""
DEVStone atomic model for the pyjevsim benchmark.

The DEVStone atomic has a single passive/active state machine:
  - passive (initial, deadline = inf): waits for an input event.
  - active  (deadline = int_delay): on entry the model is committed to emit
    output(s); on int_trans it returns to passive.

To make the workload comparable to the canonical DEVStone benchmark, ext_trans
optionally performs a synthetic CPU load (Dhrystone-style busy work). By default
the load is zero so the benchmark measures simulator overhead, not user code.
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.system_message import SysMessage


def _do_dhrystone_work(iterations):
    if iterations <= 0:
        return 0
    acc = 0
    for i in range(iterations):
        acc = (acc + i) ^ (i << 1)
    return acc


class DEVStoneAtomic(BehaviorModel):
    """A single atomic block of the DEVStone benchmark.

    Args:
        name (str): Unique model name.
        out_ports (list[str]): Output ports the model emits on every internal
            transition. Use one port for LI/HI, multiple ports for HO.
        int_delay (float): Time spent in the active state. 0 keeps the
            simulator advancing without inserting artificial real-time waits.
        dhrystones (int): Synthetic CPU work performed inside ext_trans.
    """

    def __init__(self, name, out_ports=("out",), int_delay=0.0, dhrystones=0):
        super().__init__(name)

        self.insert_state("passive")
        self.insert_state("active", int_delay)
        self.init_state("passive")

        self.insert_input_port("in")
        self._out_ports = list(out_ports)
        for port in self._out_ports:
            self.insert_output_port(port)

        self._dhrystones = dhrystones
        self._ext_count = 0
        self._int_count = 0

    def ext_trans(self, port, msg):
        if port != "in":
            return
        self._ext_count += 1
        _do_dhrystone_work(self._dhrystones)
        self._cur_state = "active"

    def int_trans(self):
        if self._cur_state == "active":
            self._int_count += 1
            self._cur_state = "passive"

    def output(self, msg_deliver):
        for port in self._out_ports:
            sys_msg = SysMessage(self.get_name(), port)
            sys_msg.insert(1)
            msg_deliver.insert_message(sys_msg)

    def get_counts(self):
        return self._ext_count, self._int_count


class DEVStoneGenerator(BehaviorModel):
    """Periodic event source. Fires `count` events spaced by `period`."""

    def __init__(self, name, period=1.0, count=10):
        super().__init__(name)

        self.insert_state("active", period)
        self.insert_state("done")
        self.init_state("active")

        self.insert_input_port("start")
        self.insert_output_port("out")

        self._period = period
        self._remaining = count
        self._fired = 0

    def ext_trans(self, port, msg):
        # Generator runs autonomously once registered; ignore inputs.
        pass

    def int_trans(self):
        if self._cur_state != "active":
            return
        self._fired += 1
        self._remaining -= 1
        if self._remaining <= 0:
            self._cur_state = "done"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            sys_msg = SysMessage(self.get_name(), "out")
            sys_msg.insert(self._fired + 1)
            msg_deliver.insert_message(sys_msg)

    def get_fired(self):
        return self._fired


class DEVStoneSink(BehaviorModel):
    """Counts inbound events and stays passive forever."""

    def __init__(self, name):
        super().__init__(name)
        self.insert_state("passive")
        self.init_state("passive")

        self.insert_input_port("in")

        self._received = 0

    def ext_trans(self, port, msg):
        if port == "in":
            self._received += 1

    def int_trans(self):
        pass

    def output(self, msg_deliver):
        pass

    def get_received(self):
        return self._received
