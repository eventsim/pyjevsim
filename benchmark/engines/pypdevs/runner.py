"""PythonPDEVS DEVStone runner (uses the minimal kernel)."""

import time

from benchmark.engines.common import RunResult


ENGINE_NAME = "pypdevs"


def is_available() -> bool:
    try:
        from pypdevs.minimal import Simulator  # noqa: F401
        return True
    except Exception:
        return False


def run(variant: str, depth: int, width: int,
        int_cycles: int = 0, ext_cycles: int = 0) -> RunResult:
    from pypdevs.minimal import Simulator

    from .topology import DEVStoneRoot

    result = RunResult(
        engine=ENGINE_NAME,
        variant=variant,
        depth=depth,
        width=width,
        int_cycles=int_cycles,
        ext_cycles=ext_cycles,
    )

    t0 = time.perf_counter()
    root = DEVStoneRoot(variant, depth, width, int_cycles, ext_cycles)
    t1 = time.perf_counter()

    sim = Simulator(root)
    # The DEVStone cascade completes within a tiny simulated horizon since
    # all transitions use sigma=0; bound it generously.
    sim.setTerminationTime(max(8.0, depth * width + 4.0))
    t2 = time.perf_counter()

    sim.simulate()
    t3 = time.perf_counter()

    result.model_build_s = t1 - t0
    result.engine_setup_s = t2 - t1
    result.sim_s = t3 - t2
    result.total_s = t3 - t0
    result.n_atomics = len(root.atomics)
    result.n_internals = sum(a.n_internals for a in root.atomics)
    result.n_externals = sum(a.n_externals for a in root.atomics)
    result.n_events = sum(a.n_events for a in root.atomics)
    return result
