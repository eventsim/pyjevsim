"""Shared types and helpers for engine adapters.

A `RunResult` captures timing breakdown plus the static counts that come from
the DEVStone topology (atomics, couplings, transitions). Every engine adapter
returns the same dataclass so the cross-engine runner can tabulate results
without engine-specific knowledge.
"""

from dataclasses import dataclass, asdict, field


VARIANTS = ("LI", "HI", "HO", "HOmod")


@dataclass
class RunResult:
    engine: str
    variant: str
    depth: int
    width: int
    int_cycles: int = 0
    ext_cycles: int = 0

    # Timing breakdown (seconds)
    model_build_s: float = 0.0
    engine_setup_s: float = 0.0
    sim_s: float = 0.0
    total_s: float = 0.0

    # Static / dynamic counts (best-effort — some engines do not report all)
    n_atomics: int = 0
    n_internals: int = 0
    n_externals: int = 0
    n_events: int = 0

    error: str = ""

    # Multi-event mode: `events` seed events injected into the root input at
    # simulated times 0, period, 2*period, ... (events == 1 is the original
    # single-seed cascade). The seed generator's own transitions are never
    # counted in n_internals / n_externals.
    events: int = 1
    period: float = 1.0
    # How the seeds reach the root input: "generator" (a seed atomic inside
    # the simulated model; pyjevsim, pypdevs, reference, and xdevs with
    # events > 1) or "inject" (xdevs' historical Coordinator.inject path).
    seed: str = ""

    @property
    def transitions(self) -> int:
        return self.n_internals + self.n_externals

    @property
    def transitions_per_s(self) -> float:
        return self.transitions / self.sim_s if self.sim_s else 0.0

    def as_dict(self) -> dict:
        # Column order: the original columns first (unchanged), then the
        # multi-event columns appended at the end so older CSV readers that
        # index by position keep working.
        d = asdict(self)
        events = d.pop("events")
        period = d.pop("period")
        seed = d.pop("seed")
        d["transitions"] = self.transitions
        d["transitions_per_s"] = round(self.transitions_per_s, 2)
        d["events"] = events
        d["period"] = period
        d["seed"] = seed
        return d


def check_events(events: int, period: float):
    """Validate multi-event arguments shared by every adapter."""
    if int(events) != events or events < 1:
        raise ValueError(f"events must be an integer >= 1, got {events!r}")
    if not period > 0:
        raise ValueError(f"period must be > 0, got {period!r}")


def seed_horizon(depth: int, width: int, events: int = 1,
                 period: float = 1.0):
    """Simulated horizon that lets every seed's zero-delay cascade drain.

    events == 1 returns exactly the historical bound `max(8, d*w + 4)` (an
    int), so the single-event path is unchanged.
    """
    base = max(8, depth * width + 4)
    if events == 1:
        return base
    return (events - 1) * period + base


def expected_atomic_count(variant: str, depth: int, width: int) -> int:
    """Return the expected atomic count for a DEVStone configuration.

    The formulas follow the recursive shape: a depth-1 model is a single
    atomic; each additional level adds (width - 1) atomics for LI/HI/HO and
    more for HOmod.
    """
    variant = variant.upper()
    if depth < 1 or width < 1:
        raise ValueError("depth and width must be >= 1")
    if variant in ("LI", "HI", "HO"):
        return 1 + (depth - 1) * (width - 1)
    if variant == "HOmod":
        if depth == 1:
            return 1
        # First level: width - 1 atomics in row 1, plus a triangular block.
        per_level = (width - 1) + sum(range(1, width))
        return 1 + (depth - 1) * per_level
    raise ValueError(f"unknown variant {variant}")
