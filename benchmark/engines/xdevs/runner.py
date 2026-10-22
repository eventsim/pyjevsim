"""xdevs (xdevs.py) DEVStone runner.

Uses the canonical implementation that ships with `xdevs.examples.devstone`.
A single seed event is injected into the root model; the coordinator then
drains the event queue with `simulate_iters()`.

Multi-event mode (events > 1)
-----------------------------
`Coordinator.inject(port, values, e)` in xdevs 3.0.0 executes the root
`deltfcn` synchronously at `time_last + e`, so it cannot pre-schedule a
train of seeds. Instead, for events > 1 the root is wrapped in a coupled
model together with a periodic seed generator (the same shape as xdevs'
own `examples.devstone.DEVStone` wrapper with its `Seeder`), coupled to
every root input port. The generator lives outside `root`, so its
transitions never enter `root.n_internals` / `root.n_externals`.

`seed="auto"` (default) keeps the historical inject path for events == 1
and uses the generator for events > 1; `seed="generator"` forces the
generator path also for events == 1 (CLI: `--xdevs-seed generator`).

Two caveats of the historical inject path (events == 1, seed="auto"),
kept unchanged so old numbers stay reproducible:

  - Timing: each inject() call runs a root deltfcn, i.e. the first wave of
    external transitions (one per atomic fed by the seed), before the sim
    timer starts, so sim_s excludes that work.
  - HO transition deficit: HO has two root input ports (i_in, i_in2) and
    they are injected by two successive inject() calls at t=0. The second
    call's deltfcn finds the atomics activated by the first call imminent
    and runs their deltint without a preceding lambdaf, so their outputs
    are lost and the cascade is shorter (HO 4x4: 26 transitions instead of
    the 38 every other engine and the generator path report).

The generator path delivers all root input ports in one bag inside the
timed simulate() call, like the generator-based seeding of the other three
adapters, and has neither caveat.
"""

import time

from benchmark.engines.common import RunResult, check_events


ENGINE_NAME = "xdevs"


def is_available() -> bool:
    try:
        import xdevs  # noqa: F401
        from xdevs.examples.devstone import devstone  # noqa: F401
        return True
    except Exception:
        return False


def _periodic_wrapper(root, events: int, period: float):
    """Coupled(root + seed generator firing at 0, period, 2*period, ...)."""
    from xdevs.models import Atomic, Coupled, Port

    class PeriodicSeeder(Atomic):
        def __init__(self, name: str):
            super().__init__(name)
            self.o_out = Port(int, "o_out")
            self.add_out_port(self.o_out)
            self.remaining = events

        def initialize(self):
            self.activate()

        def deltint(self):
            self.remaining -= 1
            if self.remaining > 0:
                self.hold_in("wait", period)
            else:
                self.passivate()

        def deltext(self, e):
            pass

        def lambdaf(self):
            self.o_out.add(0)

        def exit(self):
            pass

    top = Coupled("bench_top")
    seeder = PeriodicSeeder("seeder")
    top.add_component(seeder)
    top.add_component(root)
    for port in root.in_ports:
        top.add_coupling(seeder.o_out, port)
    return top


def run(variant: str, depth: int, width: int,
        int_cycles: int = 0, ext_cycles: int = 0,
        events: int = 1, period: float = 1.0,
        seed: str = "auto") -> RunResult:
    from xdevs.sim import Coordinator
    from xdevs.examples.devstone.devstone import LI, HI, HO, HOmod

    check_events(events, period)
    if seed not in ("auto", "generator"):
        raise ValueError(f"seed must be 'auto' or 'generator', got {seed!r}")
    use_inject = events == 1 and seed == "auto"

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
        events=events,
        period=period,
        seed="inject" if use_inject else "generator",
    )

    t0 = time.perf_counter()
    # `test=True` enables transition counters used in the output stats.
    root = cls(f"{variant}_root", width, depth, int_cycles, ext_cycles, test=True)
    t1 = time.perf_counter()

    if use_inject:
        coord = Coordinator(root)
        coord.initialize()
        # Single seed event into every external input port of the root.
        for port in root.in_ports:
            coord.inject(port, 0)
        num_iters = 1_000_000
    else:
        coord = Coordinator(_periodic_wrapper(root, events, period))
        coord.initialize()
        # The loop stops when the clock reaches INFINITY; the cap only
        # guards against a runaway model.
        num_iters = 1_000_000 * events
    t2 = time.perf_counter()

    # `simulate_iters` was renamed in newer xdevs releases. Prefer the new
    # API and fall back if a vendored copy still exposes the old name.
    if hasattr(coord, "simulate"):
        coord.simulate(num_iters=num_iters)
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
