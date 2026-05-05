"""Reference (hand-rolled) DEVS engine DEVStone runner."""

import time

from benchmark.engines.common import RunResult
from .topology import build


ENGINE_NAME = "reference"


def is_available() -> bool:
    return True


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
    eng, atomics, _levels = build(variant, depth, width, int_cycles, ext_cycles)
    t1 = time.perf_counter()

    eng.initialize()
    t2 = time.perf_counter()

    eng.run()
    t3 = time.perf_counter()

    result.model_build_s = t1 - t0
    result.engine_setup_s = t2 - t1
    result.sim_s = t3 - t2
    result.total_s = t3 - t0
    result.n_atomics = len(atomics)
    result.n_internals = sum(a.n_internals for a in atomics)
    result.n_externals = sum(a.n_externals for a in atomics)
    result.n_events = sum(a.n_events for a in atomics)
    return result
