"""pypdevs sparse-time runner — periodic generator → counting sink."""

import time

from benchmark.engines.common import RunResult


ENGINE_NAME = "pypdevs"
INF = float("inf")


def is_available() -> bool:
    try:
        from pypdevs.minimal import Simulator  # noqa: F401
        return True
    except Exception:
        return False


def run_sparse(period: float, count: int) -> RunResult:
    from pypdevs.minimal import AtomicDEVS, CoupledDEVS, Simulator

    class PeriodicGen(AtomicDEVS):
        def __init__(self):
            super().__init__("gen")
            self.outp = self.addOutPort("out")
            self.state = "active"
            self.fired = 0
            self.elapsed = 0.0

        def timeAdvance(self):
            return period if self.state == "active" else INF

        def intTransition(self):
            self.fired += 1
            return "active" if self.fired < count else "done"

        def outputFnc(self):
            return {self.outp: [self.fired]}

    class CountingSink(AtomicDEVS):
        def __init__(self):
            super().__init__("sink")
            self.inp = self.addInPort("in")
            self.state = "passive"
            self.received = 0

        def timeAdvance(self):
            return INF

        def extTransition(self, inputs):
            for port_msgs in inputs.values():
                self.received += len(port_msgs)
            return "passive"

    class Root(CoupledDEVS):
        def __init__(self):
            super().__init__("root")
            self.gen = self.addSubModel(PeriodicGen())
            self.sink = self.addSubModel(CountingSink())
            self.connectPorts(self.gen.outp, self.sink.inp)

    result = RunResult(
        engine=ENGINE_NAME,
        variant=f"sparse_p{int(period)}",
        depth=1,
        width=1,
    )

    t0 = time.perf_counter()
    root = Root()
    t1 = time.perf_counter()

    sim = Simulator(root)
    sim.setTerminationTime(period * count + 4)
    t2 = time.perf_counter()

    sim.simulate()
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
