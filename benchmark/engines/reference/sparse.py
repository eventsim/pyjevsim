"""Reference engine sparse-time runner — periodic generator → counting sink."""

import time

from benchmark.engines.common import RunResult
from .engine import Atomic, Engine, INFINITY


ENGINE_NAME = "reference"


def is_available() -> bool:
    return True


def run_sparse(period: float, count: int) -> RunResult:
    class PeriodicGen(Atomic):
        __slots__ = ("fired",)

        def __init__(self, name: str):
            super().__init__(name)
            self.fired = 0

        def initialize(self):
            self.sigma = period
            self.phase = "active"

        def deltint(self):
            self.fired += 1
            if self.fired >= count:
                self.sigma = INFINITY
                self.phase = "done"
            else:
                self.sigma = period

        def lambdaf(self):
            return [self.fired]

    class CountingSink(Atomic):
        __slots__ = ("received",)

        def __init__(self, name: str):
            super().__init__(name)
            self.received = 0

        def deltext(self, e, msgs):
            self.received += len(msgs)
            self.sigma = INFINITY

    result = RunResult(
        engine=ENGINE_NAME,
        variant=f"sparse_p{int(period)}",
        depth=1,
        width=1,
    )

    t0 = time.perf_counter()
    eng = Engine()
    gen = eng.add(PeriodicGen("gen"))
    sink = eng.add(CountingSink("sink"))
    eng.couple(gen, sink)
    t1 = time.perf_counter()

    eng.initialize()
    t2 = time.perf_counter()

    eng.run()
    t3 = time.perf_counter()

    result.model_build_s = t1 - t0
    result.engine_setup_s = t2 - t1
    result.sim_s = t3 - t2
    result.total_s = t3 - t0
    result.n_atomics = 2
    result.n_internals = count
    result.n_externals = sink.received
    result.n_events = sink.received
    return result
