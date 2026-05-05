"""xdevs (xdevs.py) DEVStone runner.

Uses the canonical implementation that ships with `xdevs.examples.devstone`.
A single seed event is injected into the root model; the coordinator then
drains the event queue with `simulate_iters()`.
"""

import time

from benchmark.engines.common import RunResult


ENGINE_NAME = "xdevs"


def is_available() -> bool:
    try:
        import xdevs  # noqa: F401
        from xdevs.examples.devstone import devstone  # noqa: F401
        return True
    except Exception:
        return False


def run(variant: str, depth: int, width: int,
        int_cycles: int = 0, ext_cycles: int = 0) -> RunResult:
    from xdevs.sim import Coordinator
    from xdevs.examples.devstone.devstone import LI, HI, HO, HOmod

    cls_map = {"LI": LI, "HI": HI, "HO": HO, "HOmod": HOmod}
    if variant not in cls_map:
        raise ValueError(f"unknown variant {variant}")
    cls = cls_map[variant]

    result = RunResult(
        engine=ENGINE_NAME,
        variant=variant,
        depth=depth,
        width=width,
        int_cycles=int_cycles,
        ext_cycles=ext_cycles,
    )

    t0 = time.perf_counter()
    # `test=True` enables transition counters used in the output stats.
    root = cls(f"{variant}_root", width, depth, int_cycles, ext_cycles, test=True)
    t1 = time.perf_counter()

    coord = Coordinator(root)
    coord.initialize()
    # Single seed event into every external input port of the root.
    for port in root.in_ports:
        coord.inject(port, 0)
    t2 = time.perf_counter()

    # `simulate_iters` was renamed in newer xdevs releases. Prefer the new
    # API and fall back if a vendored copy still exposes the old name.
    if hasattr(coord, "simulate"):
        coord.simulate(num_iters=1_000_000)
    else:
        coord.simulate_iters()
    t3 = time.perf_counter()

    result.model_build_s = t1 - t0
    result.engine_setup_s = t2 - t1
    result.sim_s = t3 - t2
    result.total_s = t3 - t0
    result.n_atomics = root.n_atomics
    result.n_internals = root.n_internals
    result.n_externals = root.n_externals
    result.n_events = root.n_events
    return result
