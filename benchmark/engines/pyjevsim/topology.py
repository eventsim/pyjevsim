"""Flattened DEVStone topology for the pyjevsim benchmark adapter.

The graph mirrors the *flattened* shape of the canonical xdevs DEVStone:

  - Seeder fires exactly one event at t=0 then passivates (events=1), or
    `events` events at t = 0, period, 2*period, ... in multi-event mode.
  - LI(d, w) has 1 + (d-1) * (w-1) atomics. Seeder feeds every atomic.
  - HI adds an internal chain inside every non-innermost level:
        atomic[i].out -> atomic[i+1].in
  - HO uses the same flattened chain construction described below.

Transition counts may differ marginally between engines because pyjevsim and
xdevs implement confluent transitions differently. The cross-engine runner
reports each engine's own counters so the difference is visible.
"""

import time

from pyjevsim.definition import ExecutionType
from pyjevsim.system_executor import SysExecutor

from benchmark.engines.common import seed_horizon
from .atomic import DEVStoneAtomic, Seeder


def _atomics_per_level(depth: int, width: int) -> list[int]:
    """Innermost level has 1 atomic; each outer level adds (w - 1)."""
    return [1] + [width - 1] * (depth - 1)


def build(variant: str, depth: int, width: int,
          int_cycles: int = 0, ext_cycles: int = 0,
          events: int = 1, period: float = 1.0,
          snapshot_manager=None, snapshot_condition=None):
    """Build the flattened DEVStone graph.

    With ``snapshot_manager`` and ``snapshot_condition`` given, the
    condition is registered for every model (seeder included) before the
    model is registered with the executor, so every executor is wrapped in
    a ``SnapshotExecutor`` (the standard suite's W7 workload).
    """
    variant = variant.upper()
    if variant not in ("LI", "HI", "HO"):
        raise ValueError(f"variant {variant} not supported")
    if depth < 1 or width < 1:
        raise ValueError("depth and width must be >= 1")

    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME,
                     snapshot_manager=snapshot_manager)

    def register(model):
        if snapshot_manager is not None and snapshot_condition is not None:
            snapshot_manager.register_snapshot_condition(
                model.get_name(), snapshot_condition)
        ss.register_entity(model)

    seeder = Seeder("seeder", events=events, period=period)
    register(seeder)

    levels: list[list[DEVStoneAtomic]] = []
    for d, count in enumerate(_atomics_per_level(depth, width)):
        row = []
        for i in range(count):
            atomic = DEVStoneAtomic(
                f"a_d{d}_i{i}",
                int_cycles=int_cycles,
                ext_cycles=ext_cycles,
            )
            register(atomic)
            row.append(atomic)
        levels.append(row)

    # The seeder represents flattened external-input couplings.
    for row in levels:
        for atomic in row:
            ss.coupling_relation(seeder, "out", atomic, "in")

    # HI / HO add an intra-level chain in every non-innermost level.
    if variant in ("HI", "HO"):
        for d in range(1, depth):
            row = levels[d]
            for i in range(len(row) - 1):
                ss.coupling_relation(row[i], "out", row[i + 1], "in")

    # This flattened adapter leaves chain-tail output ports uncoupled rather
    # than adding a separate HO escape port.

    atomics = [a for row in levels for a in row]
    return ss, atomics, levels


def simulate(ss, depth: int, width: int, events: int = 1,
             period: float = 1.0):
    """Simulate until the FEL drains.

    All transitions in this adapter use deadline 0. The calculated horizon
    allows the simulator to drain its future-event list (after the last
    seed at (events - 1) * period in multi-event mode).
    """
    horizon = seed_horizon(depth, width, events, period)
    ss.simulate(horizon, _tm=False)
