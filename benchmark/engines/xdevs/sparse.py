"""xdevs sparse-time runner — periodic generator → counting sink."""

import time

from benchmark.engines.common import RunResult


ENGINE_NAME = "xdevs"


def is_available() -> bool:
    try:
        import xdevs  # noqa: F401
        return True
    except Exception:
        return False


def run_sparse(period: float, count: int) -> RunResult:
    from xdevs.models import Atomic, Coupled, Port
    from xdevs.sim import Coordinator

    class PeriodicGen(Atomic):
        def __init__(self):
            super().__init__("gen")
            self.o = Port(int, "o")
            self.add_out_port(self.o)
            self._fired = 0

        def initialize(self):
            self.hold_in("active", period)

        def deltint(self):
            self._fired += 1
            if self._fired >= count:
                self.passivate()
            else:
                self.hold_in("active", period)

        def deltext(self, e):
            pass

        def lambdaf(self):
            self.o.add(self._fired)

        def exit(self):
            pass

    class CountingSink(Atomic):
        def __init__(self):
            super().__init__("sink")
            self.i = Port(int, "i")
            self.add_in_port(self.i)
            self.received = 0

        def initialize(self):
            self.passivate()

        def deltint(self):
            pass

        def deltext(self, e):
            self.received += len(self.i)
            self.passivate()

        def lambdaf(self):
            pass

        def exit(self):
            pass

    class Root(Coupled):
        def __init__(self):
            super().__init__("root")
            self.gen = PeriodicGen()
            self.sink = CountingSink()
            self.add_component(self.gen)
            self.add_component(self.sink)
            self.add_coupling(self.gen.o, self.sink.i)

    result = RunResult(
        engine=ENGINE_NAME,
        variant=f"sparse_p{int(period)}",
        depth=1,
        width=1,
    )

    t0 = time.perf_counter()
    root = Root()
    t1 = time.perf_counter()

    coord = Coordinator(root)
    coord.initialize()
    t2 = time.perf_counter()

    coord.simulate(num_iters=count + 8)
    t3 = time.perf_counter()

    result.model_build_s = t1 - t0
    result.engine_setup_s = t2 - t1
    result.sim_s = t3 - t2
    result.total_s = t3 - t0
    result.n_atomics = 2
    result.n_internals = count
    result.n_externals = root.sink.received
    result.n_events = root.sink.received
    return result
