"""pyjevsim sparse-time runner.

A periodic Generator emits one event every `period` simulated ticks for a
total of `count` firings; a single Sink atomic consumes them. Between
firings the executor's V_TIME loop must traverse `period` empty ticks
(`global_time += time_resolution` per iteration in
`pyjevsim/system_executor.py:390-392`). With period=1 this matches the
existing baseline; with period >> 1 the per-tick overhead dominates.
"""

import time

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage

from benchmark.engines.common import RunResult


ENGINE_NAME = "pyjevsim"


class PeriodicGen(BehaviorModel):
    def __init__(self, period: float, count: int):
        super().__init__("gen")
        self.insert_state("active", period)
        self.insert_state("done")
        self.init_state("active")
        self.insert_output_port("out")
        self._count = count
        self._fired = 0

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        if self._cur_state == "active":
            self._fired += 1
            if self._fired >= self._count:
                self._cur_state = "done"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            m = SysMessage(self.get_name(), "out")
            m.insert(self._fired)
            msg_deliver.insert_message(m)


class CountingSink(BehaviorModel):
    def __init__(self):
        super().__init__("sink")
        self.insert_state("passive")
        self.init_state("passive")
        self.insert_input_port("in")
        self.received = 0

    def ext_trans(self, port, msg):
        if port == "in":
            self.received += 1

    def int_trans(self):
        pass

    def output(self, msg_deliver):
        pass


def is_available() -> bool:
    return True


def run_sparse(period: float, count: int) -> RunResult:
    result = RunResult(
        engine=ENGINE_NAME,
        variant=f"sparse_p{int(period)}",
        depth=1,
        width=1,
    )

    t0 = time.perf_counter()
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    gen = PeriodicGen(period, count)
    sink = CountingSink()
    ss.register_entity(gen)
    ss.register_entity(sink)
    ss.coupling_relation(gen, "out", sink, "in")
    t1 = time.perf_counter()

    horizon = period * count + 4
    ss.simulate(horizon, _tm=False)
    t3 = time.perf_counter()

    result.model_build_s = t1 - t0
    result.engine_setup_s = 0.0
    result.sim_s = t3 - t1
    result.total_s = t3 - t0
    result.n_atomics = 2
    result.n_internals = count  # gen fires `count` times
    result.n_externals = sink.received  # sink receives `count` events
    result.n_events = sink.received
    return result
