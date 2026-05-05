"""pyjevsim DEVStone runner."""

import time

from benchmark.engines.common import RunResult
from .topology import build, simulate


ENGINE_NAME = "pyjevsim"


def is_available() -> bool:
    try:
        import pyjevsim  # noqa: F401
        return True
    except Exception:
        return False


def run(variant: str, depth: int, width: int,
        int_cycles: int = 0, ext_cycles: int = 0) -> RunResult:
    result = RunResult(
        engine=ENGINE_NAME,
        variant=variant,
        depth=depth,
        width=width,
        int_cycles=int_cycles,
        ext_cycles=ext_cycles,
    )

    t0 = time.perf_counter()
    ss, atomics, _levels = build(variant, depth, width, int_cycles, ext_cycles)
    t1 = time.perf_counter()

    # No real engine setup phase beyond model registration in pyjevsim.
    t2 = t1

    simulate(ss, depth, width)
    t3 = time.perf_counter()

    n_int = sum(a._n_internals for a in atomics)
    n_ext = sum(a._n_externals for a in atomics)
    n_evt = sum(a._n_events for a in atomics)

    result.model_build_s = t1 - t0
    result.engine_setup_s = t2 - t1
    result.sim_s = t3 - t2
    result.total_s = t3 - t0
    result.n_atomics = len(atomics)
    result.n_internals = n_int
    result.n_externals = n_ext
    result.n_events = n_evt
    return result
