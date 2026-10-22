"""Workloads of the standard performance suite (``python -m benchmark.suite``).

Each workload W1..W7 is a small module function ``run(params) -> dict`` that
builds a model, times only the simulation (build excluded) and returns::

    {"metrics": {"sim_s": float, ...},   # timed quantities, seconds
     "build_s": float,                   # informational, never compared
     "parity": {...},                    # deterministic outcome key
     "info": {...}}                      # extra, never compared

The suite runs every timed measurement in a fresh subprocess through
``benchmark/workloads/child.py``, which imports ``pyjevsim`` (and, for W5, the
``examples`` package) from the checkout under test and this harness from the
suite's own checkout, so base and candidate always run identical harness
code.  W6 (import / start-up time) is the exception: it is a bare
``python -c`` process (see :mod:`benchmark.workloads.startup`).

Importing this package must not import ``pyjevsim``: the registry is read by
the parent process, which never loads the engine.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Workload:
    wid: str
    title: str
    module: str          # module under benchmark.workloads
    func: str            # function name in that module
    params: dict = field(default_factory=dict)
    # Metric names in report order; the first is the headline metric.
    metrics: tuple = ("sim_s",)
    # True for W6: the parent builds a bare "python -c" command instead of
    # running child.py.
    bare_process: bool = False


WORKLOADS = {
    "W1": Workload(
        "W1", "DEVStone HI 10x10, 100 seeds (flattened adapter)",
        "devstone", "run_devstone",
        {"variant": "HI", "depth": 10, "width": 10, "events": 100,
         "period": 1.0}),
    "W2": Workload(
        "W2", "DEVStone LI 10x10, 1000 seeds (flattened adapter)",
        "devstone", "run_devstone",
        {"variant": "LI", "depth": 10, "width": 10, "events": 1000,
         "period": 1.0}),
    "W3": Workload(
        "W3", "Sparse generator->sink, count 20000, period 10",
        "sparse", "run_sparse",
        {"count": 20000, "period": 10}),
    "W4": Workload(
        "W4", "Idle-heavy: 10000 passive models + 5 ping-pong pairs, "
              "1000 events per pair",
        "idle", "run_idle",
        {"idle": 10000, "pairs": 5, "events": 1000}),
    "W5": Workload(
        "W5", "Bank example: 20 generators, queue 10, 10 accountants, "
              "seed 1, 3000 x simulate(1)",
        "bank", "run_bank",
        {"gen_num": 20, "queue_size": 10, "proc_num": 10,
         "max_user": 500000, "seed": 1, "ticks": 3000}),
    "W6": Workload(
        "W6", "Import time and start-up (import + SysExecutor(1)), "
              "bare process",
        "startup", "command",
        {}, metrics=("import_s", "startup_s", "process_s"),
        bare_process=True),
    "W7": Workload(
        "W7", "W1 topology with every executor wrapped in SnapshotExecutor",
        "devstone", "run_devstone_snapshot",
        {"variant": "HI", "depth": 10, "width": 10, "events": 100,
         "period": 1.0}),
}

DEFAULT_WORKLOADS = ("W1", "W2", "W3", "W4", "W5", "W6", "W7")


def resolve(wid):
    try:
        return WORKLOADS[wid.upper()]
    except KeyError:
        raise ValueError(
            f"unknown workload {wid!r}; known: {', '.join(WORKLOADS)}"
        ) from None
