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

    @property
    def transitions(self) -> int:
        return self.n_internals + self.n_externals

    @property
    def transitions_per_s(self) -> float:
        return self.transitions / self.sim_s if self.sim_s else 0.0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["transitions"] = self.transitions
        d["transitions_per_s"] = round(self.transitions_per_s, 2)
        return d


def expected_atomic_count(variant: str, depth: int, width: int) -> int:
    """Return the canonical atomic count for a DEVStone configuration.

    Useful for sanity-checking adapters that build the graph independently.
    Formulas follow the canonical recursive shape: a depth-1 model is a single
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
