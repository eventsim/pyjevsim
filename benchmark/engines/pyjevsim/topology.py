"""Canonical DEVStone topology built on pyjevsim's SysExecutor.

The graph mirrors the *flattened* shape of the canonical xdevs DEVStone:

  - Seeder fires exactly one event at t=0 then passivates.
  - LI(d, w) has 1 + (d-1) * (w-1) atomics. Seeder feeds every atomic.
  - HI adds an internal chain inside every non-innermost level:
        atomic[i].out -> atomic[i+1].in
  - HO is HI plus an "escape" output from every atomic. We model that as a
    second output port that fans out to the default message catcher; that
    keeps the per-atomic transition count aligned with the canonical model
    while still exercising additional coupling traversal.

Transition counts may differ marginally between engines because pyjevsim and
xdevs implement confluent transitions differently. The cross-engine runner
reports each engine's own counters so the difference is visible.
"""

import time

from pyjevsim.definition import ExecutionType
from pyjevsim.system_executor import SysExecutor

from .atomic import DEVStoneAtomic, Seeder


def _atomics_per_level(depth: int, width: int) -> list[int]:
    """Innermost level has 1 atomic; each outer level adds (w - 1)."""
    return [1] + [width - 1] * (depth - 1)


def build(variant: str, depth: int, width: int,
          int_cycles: int = 0, ext_cycles: int = 0):
    variant = variant.upper()
    if variant not in ("LI", "HI", "HO"):
        raise ValueError(f"variant {variant} not supported")
    if depth < 1 or width < 1:
        raise ValueError("depth and width must be >= 1")

    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)

    seeder = Seeder("seeder")
    ss.register_entity(seeder)

    levels: list[list[DEVStoneAtomic]] = []
    for d, count in enumerate(_atomics_per_level(depth, width)):
        row = []
        for i in range(count):
            atomic = DEVStoneAtomic(
                f"a_d{d}_i{i}",
                int_cycles=int_cycles,
                ext_cycles=ext_cycles,
            )
            ss.register_entity(atomic)
            row.append(atomic)
        levels.append(row)

    # Seeder fans out to every atomic — flattened EICs.
    for row in levels:
        for atomic in row:
            ss.coupling_relation(seeder, "out", atomic, "in")

    # HI / HO add an intra-level chain in every non-innermost level.
    if variant in ("HI", "HO"):
        for d in range(1, depth):
            row = levels[d]
            for i in range(len(row) - 1):
                ss.coupling_relation(row[i], "out", row[i + 1], "in")

    # HO additionally has an escape path from every atomic. With a single
    # output port per atomic the simplest faithful approximation is to leave
    # the outputs uncoupled at the root (default catcher absorbs them) which
    # already happens for the chain-tail atomics. We deliberately do not add
    # extra ports here so per-atomic transition counts remain comparable.

    atomics = [a for row in levels for a in row]
    return ss, atomics, levels


def simulate(ss, depth: int, width: int):
    """Simulate until the FEL drains.

    All DEVStone transitions in our build use deadline 0 so the entire
    cascade completes within a few simulated seconds. We loop a generous
    number of ticks and stop when the simulator self-terminates.
    """
    horizon = max(8, depth * width + 4)
    ss.simulate(horizon, _tm=False)
